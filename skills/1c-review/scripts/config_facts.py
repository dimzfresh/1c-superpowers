#!/usr/bin/env python3
"""Факты о конфигурации из файловой выгрузки (DumpConfigToFiles, формат Configurator XML).

Только чтение, ноль зависимостей, база 1CD не открывается. Заменяет MCP метаданных там,
где нужны режим совместимости, режим блокировок, флаги модуля, карточка объекта,
чтение модуля и поиск по коду. Форматы: Configurator XML (Configuration.xml) и EDT
(Configuration/Configuration.mdo, структура сверена с образцом из репозитория 1C-Company/GitConverter).

  python3 config_facts.py info   <выгрузка>
  python3 config_facts.py list   <выгрузка> <Вид> [подстрока]      # Вид: Documents, CommonModules, ...
  python3 config_facts.py card   <выгрузка> <Вид> <Имя>
  python3 config_facts.py read   <выгрузка> <путь/к/модулю.bsl> [с_строки] [строк]
  python3 config_facts.py search <выгрузка> <регулярное_выражение> [Вид]
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

TYPE_DIRS = (
    "Catalogs",
    "Documents",
    "InformationRegisters",
    "AccumulationRegisters",
    "AccountingRegisters",
    "CalculationRegisters",
    "ChartsOfAccounts",
    "ChartsOfCharacteristicTypes",
    "ChartsOfCalculationTypes",
    "BusinessProcesses",
    "Tasks",
    "ExchangePlans",
    "DocumentJournals",
    "Enums",
    "Reports",
    "DataProcessors",
    "Constants",
    "CommonModules",
    "CommonAttributes",
    "CommonCommands",
    "CommonForms",
    "DefinedTypes",
    "EventSubscriptions",
    "HTTPServices",
    "WebServices",
    "Roles",
    "ScheduledJobs",
    "Subsystems",
    "SessionParameters",
    "FunctionalOptions",
    "XDTOPackages",
    "CommonTemplates",
)

RU_KIND = {
    "Catalogs": "Справочник",
    "Documents": "Документ",
    "InformationRegisters": "РегистрСведений",
    "AccumulationRegisters": "РегистрНакопления",
    "AccountingRegisters": "РегистрБухгалтерии",
    "CalculationRegisters": "РегистрРасчета",
    "ChartsOfAccounts": "ПланСчетов",
    "ChartsOfCharacteristicTypes": "ПланВидовХарактеристик",
    "ChartsOfCalculationTypes": "ПланВидовРасчета",
    "BusinessProcesses": "БизнесПроцесс",
    "Tasks": "Задача",
    "ExchangePlans": "ПланОбмена",
    "DocumentJournals": "ЖурналДокументов",
    "Enums": "Перечисление",
    "Reports": "Отчет",
    "DataProcessors": "Обработка",
    "Constants": "Константа",
    "CommonModules": "ОбщийМодуль",
    "CommonAttributes": "ОбщийРеквизит",
    "CommonCommands": "ОбщаяКоманда",
    "CommonForms": "ОбщаяФорма",
    "DefinedTypes": "ОпределяемыйТип",
    "EventSubscriptions": "ПодпискаНаСобытие",
    "HTTPServices": "HTTPСервис",
    "WebServices": "WebСервис",
    "Roles": "Роль",
    "ScheduledJobs": "РегламентноеЗадание",
    "Subsystems": "Подсистема",
    "SessionParameters": "ПараметрСеанса",
    "FunctionalOptions": "ФункциональнаяОпция",
    "XDTOPackages": "ПакетXDTO",
    "CommonTemplates": "ОбщийМакет",
}

INTERESTING = {
    "Name",
    "Server",
    "ServerCall",
    "Privileged",
    "ClientManagedApplication",
    "ClientOrdinaryApplication",
    "ExternalConnection",
    "Global",
    "ReturnValuesReuse",
    "Posting",
    "RealTimePosting",
    "RegisterRecords",
    "DataLockControlMode",
    "CompatibilityMode",
    "ScriptVariant",
    "DefaultRunMode",
    "Handler",
    "Event",
    "Source",
    "Template",
    "HTTPMethod",
    "RootURL",
    "Comment",
}


class DumpError(Exception):
    pass


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if local_name(child.tag) == name]


def first(element: ET.Element, name: str) -> ET.Element | None:
    for child in element:
        if local_name(child.tag) == name:
            return child
    return None


def text(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def synonym_of(props: ET.Element | None) -> str:
    if props is None:
        return ""
    synonym = first(props, "Synonym")
    if synonym is None:
        return ""
    for node in synonym.iter():
        if local_name(node.tag) == "content" and text(node):
            return text(node)
    return ""


def edt_config(root: Path) -> Path | None:
    """Путь к Configuration.mdo, если каталог это проект EDT (корень проекта или его src)."""
    for candidate in (root / "Configuration" / "Configuration.mdo", root / "src" / "Configuration" / "Configuration.mdo"):
        if candidate.is_file():
            return candidate
    return None


def edt_root(root: Path) -> Path | None:
    config = edt_config(root)
    return config.parent.parent if config is not None else None


def safe_root(root: Path) -> Path:
    resolved = root.expanduser().resolve()
    if not resolved.is_dir():
        raise DumpError(f"Каталог выгрузки не найден: {resolved}")
    if any(resolved.glob("*.1CD")) or any(resolved.glob("*.1cd")):
        raise DumpError("В каталоге лежит файл базы 1CD. Этот скрипт его не открывает.")
    if (resolved / "Configuration.xml").is_file():
        return resolved
    edt = edt_root(resolved)
    if edt is not None:
        return edt
    raise DumpError(
        "В каталоге нет Configuration.xml (Configurator) или Configuration/Configuration.mdo (EDT). Нужна выгрузка в файлы, не файл 1CD."
    )


def is_edt(root: Path) -> bool:
    return not (root / "Configuration.xml").is_file() and (root / "Configuration" / "Configuration.mdo").is_file()


EDT_SKIP = {"name", "synonym", "comment", "producedTypes", "attributes", "tabularSections", "forms", "commands", "templates",
            "dimensions", "resources", "containedObjects", "standardAttributes", "inputByString", "basedOn", "characteristics"}


def edt_scalars(node: ET.Element) -> dict[str, str]:
    found: dict[str, str] = {}
    for child in node:
        name = local_name(child.tag)
        if name in EDT_SKIP or len(child) or not text(child):
            continue
        found[name] = text(child)
    return found


def edt_info(root: Path) -> str:
    tree = parse_xml(root / "Configuration" / "Configuration.mdo")
    scalars = edt_scalars(tree)
    synonym = ""
    syn = first(tree, "synonym")
    if syn is not None:
        synonym = text(first(syn, "value"))
    counts: dict[str, int] = {}
    for child in tree:
        tag = local_name(child.tag)
        if tag in EDT_KIND_TAGS and text(child):
            counts[tag] = counts.get(tag, 0) + 1
    lines = [
        f"Имя: {text(first(tree, 'name')) or '—'}",
        f"Синоним: {synonym or '—'}",
        f"Версия конфигурации: {scalars.get('version', '—')}",
        f"Поставщик: {scalars.get('vendor', '—')}",
        f"Режим совместимости: {scalars.get('compatibilityMode', '—')}",
        f"Модальность: {scalars.get('modalityUseMode', '—')}",
        "Версия установленной платформы: в выгрузке нет",
        f"БСП: {bsp_version(root)}",
        f"Блокировки: {scalars.get('dataLockControlMode', '—')}",
        f"Вариант языка: {scalars.get('scriptVariant', '—')}",
        f"Режим запуска: {scalars.get('defaultRunMode', '—')}",
        "Формат выгрузки: EDT (.mdo)",
    ]
    if counts:
        lines.append("Состав: " + ", ".join(f"{EDT_KIND_TAGS[k]}: {n}" for k, n in sorted(counts.items())))
    lines.append("Только чтение. База 1CD и запись конфигурации недоступны.")
    return "\n".join(lines)


EDT_KIND_TAGS = {
    "catalogs": "Справочник", "documents": "Документ", "commonModules": "ОбщийМодуль", "informationRegisters": "РегистрСведений",
    "accumulationRegisters": "РегистрНакопления", "enums": "Перечисление", "reports": "Отчет", "dataProcessors": "Обработка",
    "constants": "Константа", "httpServices": "HTTPСервис", "webServices": "ВебСервис", "roles": "Роль", "scheduledJobs": "РегламентноеЗадание",
    "exchangePlans": "ПланОбмена", "eventSubscriptions": "ПодпискаНаСобытие", "subsystems": "Подсистема", "commonForms": "ОбщаяФорма",
}


def edt_object_card(root: Path, kind: str, name: str) -> str:
    path = root / kind / name / f"{name}.mdo"
    if not path.is_file():
        raise DumpError(f"Объект не найден: {kind}/{name}")
    tree = parse_xml(path)
    ru = RU_KIND.get(kind, kind)
    lines = [f"{ru}.{name}"]
    syn = first(tree, "synonym")
    if syn is not None and text(first(syn, "value")):
        lines.append(f"Синоним: {text(first(syn, 'value'))}")
    flags = edt_scalars(tree)
    if flags:
        lines.append("Свойства: " + ", ".join(f"{k}={v}" for k, v in flags.items()))
    attributes = [text(first(c, "name")) for c in tree if local_name(c.tag) == "attributes" and text(first(c, "name"))]
    if attributes:
        lines.append("Реквизиты: " + ", ".join(attributes))
    tables = []
    for c in tree:
        if local_name(c.tag) == "tabularSections":
            cols = [text(first(a, "name")) for a in c if local_name(a.tag) == "attributes" and text(first(a, "name"))]
            tname = text(first(c, "name"))
            tables.append(f"{tname}: {', '.join(cols)}" if cols else tname)
    if tables:
        lines.append("Табличные части:")
        lines.extend(f"  {row}" for row in tables)
    modules = list_bsl(path.parent, root)
    lines.append("Модули:")
    lines.extend(f"  {m}" for m in modules[:50] or ["  нет"])
    return "\n".join(lines)


def safe_file(root: Path, relative: str) -> Path:
    if not relative or relative.startswith(("/", "\\")):
        raise DumpError("Нужен путь относительно корня выгрузки.")
    candidate = (root / relative).resolve()
    if root not in candidate.parents and candidate != root:
        raise DumpError("Путь выходит за каталог выгрузки.")
    if candidate.suffix.lower() == ".1cd":
        raise DumpError("Файл базы не читается.")
    if not candidate.is_file():
        raise DumpError(f"Файл не найден: {relative}")
    return candidate


def parse_xml(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise DumpError(f"XML не разобран: {path.name}: {exc}") from exc


def properties_map(props: ET.Element | None) -> dict[str, str]:
    if props is None:
        return {}
    found: dict[str, str] = {}
    for child in props:
        name = local_name(child.tag)
        if name in INTERESTING and text(child):
            found[name] = text(child)
    return found


def named_children(container: ET.Element | None) -> list[tuple[str, str, ET.Element]]:
    if container is None:
        return []
    rows: list[tuple[str, str, ET.Element]] = []
    for child in container:
        props = first(child, "Properties")
        name = text(first(props, "Name")) if props is not None else text(child)
        if name:
            rows.append((local_name(child.tag), name, child))
    return rows


def object_xml(root: Path, kind: str, name: str) -> Path | None:
    if kind not in TYPE_DIRS:
        raise DumpError(f"Неизвестный вид метаданных: {kind}")
    folder = root / kind
    nested = folder / name / f"{name}.xml"
    flat = folder / f"{name}.xml"
    if nested.is_file():
        return nested
    if flat.is_file():
        return flat
    return None


def object_dir(root: Path, kind: str, name: str) -> Path | None:
    xml_path = object_xml(root, kind, name)
    if xml_path is None:
        return None
    if xml_path.parent.name == name:
        return xml_path.parent
    sibling = xml_path.parent / name
    if sibling.is_dir():
        return sibling
    return xml_path.parent


def list_bsl(directory: Path | None, root: Path) -> list[str]:
    if directory is None or not directory.is_dir():
        return []
    return sorted(
        path.relative_to(root).as_posix()
        for path in directory.rglob("*.bsl")
        if path.is_file()
    )


BSP_NAME = re.compile(r'Описание\.Имя\s*=\s*"СтандартныеПодсистемы"')
BSP_VERSION = re.compile(r'Описание\.Версия\s*=\s*"(\d+(?:\.\d+){1,3})"')


def bsp_version(root: Path) -> str:
    """Номер БСП из модуля, который регистрирует подсистему. Регистр базы не читается."""
    modules = root / "CommonModules"
    found_name = False
    if modules.is_dir():
        for path in modules.rglob("*.bsl"):
            if not path.is_file() or path.stat().st_size > 2_000_000:
                continue
            source = path.read_text(encoding="utf-8", errors="replace")
            if "СтандартныеПодсистемы" not in source or "Описание.Версия" not in source:
                continue
            lines = source.splitlines()
            for index, line in enumerate(lines):
                if not BSP_NAME.search(line):
                    continue
                found_name = True
                window = "\n".join(lines[max(0, index - 20) : index + 21])
                match = BSP_VERSION.search(window)
                if match:
                    relative = path.relative_to(root).as_posix()
                    return f"{match.group(1)} ({relative}:{index + 1})"
    subsystem = (root / "Subsystems" / "СтандартныеПодсистемы").is_dir() or (
        root / "Subsystems" / "СтандартныеПодсистемы.xml"
    ).is_file()
    if found_name or subsystem:
        return "подсистема есть, версия в модуле регистрации не найдена"
    return "в выгрузке нет"


def config_info(root: Path) -> str:
    root = safe_root(root)
    if is_edt(root):
        return edt_info(root)
    tree = parse_xml(root / "Configuration.xml")
    configuration = first(tree, "Configuration")
    if configuration is None:
        raise DumpError("В Configuration.xml нет узла Configuration.")
    props = first(configuration, "Properties")
    name = text(first(props, "Name")) if props is not None else ""
    lines = [
        f"Имя: {name or '—'}",
        f"Синоним: {synonym_of(props) or '—'}",
        f"Версия конфигурации: {text(first(props, 'Version')) or '—'}",
        f"Поставщик: {text(first(props, 'Vendor')) or '—'}",
        f"Режим совместимости: {text(first(props, 'CompatibilityMode')) or '—'}",
        f"Модальность: {text(first(props, 'ModalityUseMode')) or '—'}",
        "Версия установленной платформы: в выгрузке нет",
        f"БСП: {bsp_version(root)}",
        f"Блокировки: {text(first(props, 'DataLockControlMode')) or '—'}",
        f"Вариант языка: {text(first(props, 'ScriptVariant')) or '—'}",
        f"Режим запуска: {text(first(props, 'DefaultRunMode')) or '—'}",
        f"Формат выгрузки: {tree.attrib.get('version', '—')}",
    ]
    counts = []
    for kind in TYPE_DIRS:
        folder = root / kind
        if not folder.is_dir():
            continue
        amount = len(list_object_names(root, kind))
        if amount:
            counts.append(f"{RU_KIND.get(kind, kind)}: {amount}")
    if counts:
        lines.append("Состав: " + ", ".join(counts))
    lines.append("Только чтение. База 1CD и запись конфигурации недоступны.")
    return "\n".join(lines)


def list_object_names(root: Path, kind: str) -> list[str]:
    folder = root / kind
    if not folder.is_dir():
        return []
    names: set[str] = set()
    for path in folder.iterdir():
        if path.is_dir() and (path / f"{path.name}.mdo").is_file():
            names.add(path.name)
    for path in folder.glob("*.xml"):
        names.add(path.stem)
    for path in folder.iterdir():
        if path.is_dir() and (path / f"{path.name}.xml").is_file():
            names.add(path.name)
    return sorted(names)


def list_objects(root: Path, kind: str, name_contains: str = "", limit: int = 50) -> str:
    root = safe_root(root)
    if kind not in TYPE_DIRS:
        raise DumpError(
            "Вид метаданных задаётся каталогом выгрузки: Documents, CommonModules, HTTPServices…"
        )
    limit = max(1, min(limit, 200))
    needle = name_contains.casefold()
    names = [
        name
        for name in list_object_names(root, kind)
        if needle in name.casefold()
    ]
    shown = names[:limit]
    title = RU_KIND.get(kind, kind)
    lines = [f"{title}: {len(names)}"]
    lines.extend(shown)
    if len(names) > limit:
        lines.append(f"… ещё {len(names) - limit}, сузьте name_contains")
    if not names:
        lines.append("Ничего не найдено.")
    return "\n".join(lines)


def object_card(root: Path, kind: str, name: str) -> str:
    root = safe_root(root)
    if is_edt(root):
        return edt_object_card(root, kind, name)
    xml_path = object_xml(root, kind, name)
    if xml_path is None:
        raise DumpError(f"Объект не найден: {kind}/{name}")
    tree = parse_xml(xml_path)
    body = next((child for child in tree if local_name(child.tag) != "InternalInfo"), tree)
    props = first(body, "Properties")
    if props is None:
        props = first(tree, "Properties")
    ru = RU_KIND.get(kind, kind)
    lines = [f"{ru}.{name}"]
    synonym = synonym_of(props)
    if synonym:
        lines.append(f"Синоним: {synonym}")
    flags = properties_map(props)
    flags.pop("Name", None)
    if flags:
        lines.append(
            "Свойства: " + ", ".join(f"{key}={value}" for key, value in flags.items())
        )
    child_box = first(body, "ChildObjects")
    attributes = []
    tables = []
    other = []
    for tag, child_name, node in named_children(child_box):
        if tag == "Attribute":
            attributes.append(child_name)
        elif tag == "TabularSection":
            columns = [
                column_name
                for column_tag, column_name, _ in named_children(first(node, "ChildObjects"))
                if column_tag == "Attribute"
            ]
            tables.append(
                f"{child_name}: {', '.join(columns)}" if columns else child_name
            )
        elif tag in {"URLTemplate", "Method", "Dimension", "Resource", "Command", "Form", "Template"}:
            other.append(f"{tag}.{child_name}")
        else:
            other.append(f"{tag}.{child_name}")
    if attributes:
        lines.append("Реквизиты: " + ", ".join(attributes))
    if tables:
        lines.append("Табличные части:")
        lines.extend(f"  {row}" for row in tables)
    if other:
        lines.append("Вложенные: " + ", ".join(other[:40]))
    modules = list_bsl(object_dir(root, kind, name), root)
    # Общий модуль иногда лежит рядом с xml, а не внутри одноимённой папки.
    if not modules:
        sibling = xml_path.with_suffix("") 
        modules = list_bsl(sibling if sibling.is_dir() else None, root)
    lines.append("Модули:")
    lines.extend(f"  {path}" for path in modules[:50] or ["  нет"])
    return "\n".join(lines)


def read_module(root: Path, relative: str, offset: int = 1, limit: int = 200) -> str:
    root = safe_root(root)
    path = safe_file(root, relative)
    if path.suffix.lower() not in {".bsl", ".xml", ".txt", ".md"}:
        raise DumpError("Читаются только bsl, xml, txt и md.")
    offset = max(1, offset)
    limit = max(1, min(limit, 400))
    data = path.read_text(encoding="utf-8", errors="replace").splitlines()
    chunk = data[offset - 1 : offset - 1 + limit]
    header = f"{relative}:{offset}-{offset + len(chunk) - 1} из {len(data)}"
    body = "\n".join(f"{offset + index}|{line}" for index, line in enumerate(chunk))
    return header + "\n" + body


def search_code(
    root: Path,
    pattern: str,
    kind: str = "",
    limit: int = 30,
) -> str:
    root = safe_root(root)
    if not pattern or len(pattern) > 200:
        raise DumpError("Шаблон пустой или длиннее 200 символов.")
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        raise DumpError(f"Шаблон не разобран: {exc}") from exc
    limit = max(1, min(limit, 100))
    folders = [root / kind] if kind else [root]
    if kind and kind not in TYPE_DIRS and kind != "Ext":
        raise DumpError(f"Неизвестный вид: {kind}")
    hits: list[str] = []
    for folder in folders:
        if not folder.exists():
            continue
        for path in folder.rglob("*.bsl"):
            if not path.is_file() or path.stat().st_size > 2_000_000:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for number, line in enumerate(lines, start=1):
                if regex.search(line):
                    relative = path.relative_to(root).as_posix()
                    hits.append(f"{relative}:{number}: {line.strip()[:240]}")
                    if len(hits) >= limit:
                        return "\n".join(hits)
    return "\n".join(hits) if hits else "Совпадений нет."


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in {"info", "list", "card", "read", "search"}:
        print(__doc__)
        return 2
    command, root = argv[0], Path(argv[1])
    try:
        if command == "info":
            print(config_info(root))
        elif command == "list" and len(argv) >= 3:
            print(list_objects(root, argv[2], argv[3] if len(argv) > 3 else ""))
        elif command == "card" and len(argv) >= 4:
            print(object_card(root, argv[2], argv[3]))
        elif command == "read" and len(argv) >= 3:
            print(read_module(root, argv[2], int(argv[3]) if len(argv) > 3 else 1, int(argv[4]) if len(argv) > 4 else 200))
        elif command == "search" and len(argv) >= 3:
            print(search_code(root, argv[2], argv[3] if len(argv) > 3 else ""))
        else:
            print(__doc__)
            return 2
    except DumpError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
