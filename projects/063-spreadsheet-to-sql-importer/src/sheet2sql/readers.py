"""Readers that turn CSV / XLSX files into a header plus a row iterator.

Readers are *re-iterable*: calling ``rows()`` again starts from the top.
This lets the importer do two passes (infer, then load) without holding the
whole file in memory.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


class ReaderError(Exception):
    pass


@dataclass
class Table:
    """A logical table: column names plus a way to stream its rows."""

    name: str
    header: list[str]
    _source: "_RowSource"

    def rows(self) -> Iterator[list[Any]]:
        return self._source()


class _RowSource:
    def __call__(self) -> Iterator[list[Any]]:  # pragma: no cover - interface
        raise NotImplementedError


# --- CSV --------------------------------------------------------------------


class _CsvSource(_RowSource):
    def __init__(self, path: Path, encoding: str, dialect: type[csv.Dialect] | csv.Dialect):
        self.path, self.encoding, self.dialect = path, encoding, dialect

    def __call__(self) -> Iterator[list[Any]]:
        with self.path.open(newline="", encoding=self.encoding) as f:
            reader = csv.reader(f, self.dialect)
            next(reader, None)  # skip header
            for row in reader:
                if any(cell.strip() for cell in row):  # skip blank lines
                    yield row


def _sniff_dialect(sample: str) -> type[csv.Dialect] | csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def read_csv(path: str | Path, encoding: str = "utf-8-sig", delimiter: str | None = None) -> Table:
    """Open a delimited text file. The delimiter is sniffed unless given.

    ``utf-8-sig`` transparently strips the byte-order mark Excel adds.
    """
    p = Path(path)
    if not p.exists():
        raise ReaderError(f"file not found: {p}")
    with p.open(newline="", encoding=encoding) as f:
        sample = f.read(64 * 1024)
    if not sample.strip():
        raise ReaderError(f"{p} is empty")

    if delimiter is not None:
        class _D(csv.excel):
            pass
        _D.delimiter = delimiter
        dialect: Any = _D
    else:
        dialect = _sniff_dialect(sample)

    with p.open(newline="", encoding=encoding) as f:
        header = next(csv.reader(f, dialect))
    return Table(p.stem, header, _CsvSource(p, encoding, dialect))


# --- XLSX -------------------------------------------------------------------


class _XlsxSource(_RowSource):
    def __init__(self, path: Path, sheet: str, width: int):
        self.path, self.sheet, self.width = path, sheet, width

    def __call__(self) -> Iterator[list[Any]]:
        wb = _load_workbook(self.path)
        try:
            ws = wb[self.sheet]
            it = ws.iter_rows(values_only=True)
            next(it, None)  # header
            for row in it:
                cells = list(row[: self.width])
                if any(c is not None and str(c).strip() != "" for c in cells):
                    yield cells
        finally:
            wb.close()


def _load_workbook(path: Path):
    try:
        import openpyxl
    except ImportError as e:  # pragma: no cover - depends on environment
        raise ReaderError("reading .xlsx requires openpyxl: pip install openpyxl") from e
    # read_only streams rows; data_only gives cached formula results.
    return openpyxl.load_workbook(path, read_only=True, data_only=True)


def read_xlsx(path: str | Path, sheet: str | None = None) -> list[Table]:
    """Return one Table per worksheet (or just ``sheet`` if named)."""
    p = Path(path)
    if not p.exists():
        raise ReaderError(f"file not found: {p}")
    wb = _load_workbook(p)
    try:
        names = wb.sheetnames
        if sheet is not None:
            if sheet not in names:
                raise ReaderError(f"no sheet {sheet!r}; available: {', '.join(names)}")
            names = [sheet]
        tables = []
        for name in names:
            first = next(wb[name].iter_rows(values_only=True), None)
            if first is None:
                continue  # empty sheet
            header = [("" if c is None else str(c)) for c in first]
            while header and header[-1] == "":  # trim trailing empty columns
                header.pop()
            if not header:
                continue
            tables.append(Table(name, header, _XlsxSource(p, name, len(header))))
        return tables
    finally:
        wb.close()


def read_any(path: str | Path, sheet: str | None = None, delimiter: str | None = None) -> list[Table]:
    """Dispatch on file extension."""
    suffix = Path(path).suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        return read_xlsx(path, sheet)
    if suffix in (".csv", ".tsv", ".txt", ""):
        if suffix == ".tsv" and delimiter is None:
            delimiter = "\t"
        return [read_csv(path, delimiter=delimiter)]
    raise ReaderError(f"unsupported file type: {suffix}")
