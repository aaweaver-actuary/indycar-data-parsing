from indycar_data_parsing.section_times_parser import SectionTimesParser

FILE = "indycar-sectiontimes-race.pdf"
CAR_NUMBER = 2

if __name__ == "__main__":
    parser = SectionTimesParser(pdf_path=FILE, car_number=CAR_NUMBER)
    section_times_df = parser.parse_section_times()
    print(section_times_df.head())
