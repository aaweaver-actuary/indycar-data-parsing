import re
import pandas as pd
from indycar_data_parsing.pdf_reader import PDFReader


class PDFSectionExtractor:
    """
    Extracts sections from PDF text based on a header line.
    This is reusable for any PDF with repeated section headers.
    """

    def __init__(self, header: str, section_start_predicate=None):
        self.header = header
        self.section_start_predicate = section_start_predicate or (
            lambda line: line.strip() == header
        )

    def extract_sections(self, page_texts):
        """
        Yields sections (as joined text) from the given iterable of page texts.
        Each section starts with a line matching the header and ends at the next header or end of page.
        """
        for text in page_texts:
            if not text:
                continue
            lines = text.splitlines()
            idx = 0
            while idx < len(lines):
                if self.section_start_predicate(lines[idx]):
                    section_lines = [lines[idx]]
                    idx += 1
                    while idx < len(lines) and not (
                        lines[idx].strip().startswith("Section Data for Car")
                        and not self.section_start_predicate(lines[idx])
                    ):
                        section_lines.append(lines[idx])
                        idx += 1
                    yield "\n".join(section_lines)
                else:
                    idx += 1


class SectionTimesParser:
    """Parser for extracting section times from IndyCar section results PDFs."""

    def __init__(
        self,
        pdf_path: str,
        car_number: int,
        pdf_reader_cls=PDFReader,
        section_extractor_cls=PDFSectionExtractor,
    ):
        self._pdf_path = pdf_path
        self._car_number = car_number
        self._laps = []
        self._header = None
        self.is_in_car_section = False
        self._pdf_reader_cls = pdf_reader_cls
        self._section_extractor_cls = section_extractor_cls

    @property
    def pdf_path(self) -> str:
        """Returns the path to the PDF file."""
        return self._pdf_path

    @property
    def car_number(self) -> int:
        """Returns the car number for which section times are being parsed."""
        return self._car_number

    @property
    def laps(self) -> list[dict[str, str]]:
        """Returns the parsed lap and section times."""
        return self._laps

    @laps.setter
    def laps(self, value: list[dict[str, str]]) -> None:
        """Sets the parsed lap and section times."""
        self._laps = value

    @property
    def header(self) -> str:
        """Returns the header line of the section times."""
        return self._header

    @header.setter
    def header(self, value: str) -> None:
        """Sets the header line of the section times."""
        self._header = value

    @staticmethod
    def _is_header_line(line: str) -> bool:
        """Checks if a line is a header line based on its content."""
        return bool(re.match(r"Lap\s+T/S", line.strip()))

    @staticmethod
    def parse_column_names_from_header(header: str) -> list[str]:
        """Extracts column names from a header line."""
        return re.split(r"\s{1,}", header.strip())

    def get_car_section_header(self) -> str:
        """Generates the section header for the specified car number."""
        return f"Section Data for Car {self.car_number}"

    def is_end_of_current_car_section(self, text: str) -> bool:
        """Checks if the end of the current car section is reached."""
        return "Section Data for Car" in text and not self.is_in_car_section

    def create_lap_dict(
        self, col_names: list[str], lap_data: list[str]
    ) -> dict[str, str]:
        """Creates a dictionary for a lap entry with the specified column and value.

        Args:
            col_names (list[str]): The list of column names for the lap entry.
            lap_data (list[str]): The list of values for the lap entry.

        Returns:
            dict: A dictionary representing the lap entry.
        """
        return {f"{col}_time": val for col, val in zip(col_names, lap_data)}

    def update_lap_dict_with_speed_data(
        self, lap_dict: dict[str, str], speed_data: list[str]
    ) -> dict[str, str]:
        """Updates the lap dictionary with speed data.

        Args:
            lap_dict (dict[str, str]): The lap dictionary to update.
            speed_data (list[str]): The list of speed values to add to the lap dictionary.

        Returns:
            dict[str, str]: The updated lap dictionary with speed data.
        """
        for col, val in zip(list(lap_dict.keys()), speed_data):
            if col == "Lap":
                lap_dict[f"{col}_speed"] = None
            else:
                lap_dict[f"{col}_speed"] = val if val != "" else None
        return lap_dict

    def _is_new_car_section_header_in_middle_of_page(self, line: str) -> bool:
        """Checks if a new car section header is found in the middle of the page."""
        return "Section Data for Car" in line and line.strip() != self.get_car_section_header()


    def _parse_lines_for_laps(self, lines, col_names):
        """Parse lines for lap and speed data, returning a list of lap dicts."""
        laps = []
        for i, line in enumerate(lines):
            if self._is_new_car_section_header_in_middle_of_page(line):
                self.is_in_car_section = False
                break

            if self._is_header_line(line):
                col_names = self.parse_column_names_from_header(line)
                continue

            elif re.match(r"^\d+\s+T\s", line):
                lap_data = re.split(r"\s{1,}", line.strip())
                if i + 1 < len(lines) and lines[i + 1].strip().startswith("S "):
                    speed_data = re.split(r"\s{1,}", lines[i + 1].strip())
                else:
                    speed_data = []

                lap_dict = self.create_lap_dict(col_names, lap_data)
                lap_dict = self.update_lap_dict_with_speed_data(lap_dict, speed_data)
                laps.append(lap_dict)
        return laps

    @staticmethod
    def text_contains_car_section_header(text: str, car_section_header: str) -> bool:
        """Return True if any line in text matches the car section header exactly (no stripping)."""
        return any(line == car_section_header for line in text.splitlines())

    @staticmethod
    def find_car_section_header_line(text: str, car_section_header: str) -> int:
        """
        Return the index of the line that matches the car section header exactly, or -1 if not found.
        Also print lines for debugging.
        """
        lines = text.splitlines()
        print(f"DEBUG: Looking for header '{car_section_header}' in lines: {lines}")
        for idx, line in enumerate(lines):
            # Try both exact and stripped match for robustness
            if line == car_section_header:
                print(f"DEBUG: Found header at line {idx}: '{line}' (exact match)")
                return idx
            if line.strip() == car_section_header:
                print(f"DEBUG: Found header at line {idx}: '{line}' (stripped match)")
                return idx
        print("DEBUG: Header not found.")
        return -1

    def _extract_car_section_texts(self):
        """Yield text blocks for the relevant car section from the PDF."""
        car_section_header = self.get_car_section_header()
        pdf_reader = self._pdf_reader_cls(self.pdf_path)
        section_extractor = self._section_extractor_cls(car_section_header)
        return section_extractor.extract_sections(pdf_reader.read_pages())

    def parse_section_times(self) -> pd.DataFrame:
        """Extracts lap and section times for a given car number from an IndyCar section results PDF.

        Returns:
            pd.DataFrame: A DataFrame containing the lap and section times for the specified car number.
        """
        laps = []
        col_names = []
        for text in self._extract_car_section_texts():
            self.is_in_car_section = True
            lines = text.split("\n")
            laps.extend(self._parse_lines_for_laps(lines, col_names))
            # If _parse_lines_for_laps sets is_in_car_section to False, stop
            if not self.is_in_car_section:
                break

        df = pd.DataFrame(laps)
        if "Lap_time" in df.columns:
            df["Lap"] = df["Lap_time"]
            df = df.drop(columns=["Lap_time"], errors="ignore")
        return df
