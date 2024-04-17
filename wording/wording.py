import os

import docx
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docxtpl import DocxTemplate
from datetime import datetime
from docx2pdf import convert as pdf_convert

current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(current_directory)


def insert_metrics(filepath, group_num):
    doc = DocxTemplate(f"{current_directory}/generated/{filepath}.docx")
    context = {"group_num": group_num,
               "create_time": datetime.now().strftime("%d.%m.%Y в %H:%M"),
               }
    doc.render(context)
    doc.save(f"{current_directory}/generated/{filepath}.docx")


def convert_to_pdf(filepath: str):
    docx_file = f"{current_directory}/generated/{filepath}.docx"
    pdf_file = f"{current_directory}/generated/{filepath}.pdf"

    with open(pdf_file, mode="w") as file:
        file.close()

    pdf_convert(
        input_path=docx_file,
        output_path=pdf_file
    )
    if os.path.exists(docx_file):
        os.remove(docx_file)


def get_grouplist(group_list: [], group_num: int):
    filename = f"grouplist_{group_num}_{datetime.now().date().strftime('%d_%m_%Y')}"
    data = []
    for child in group_list:
        data.append(
            [
                child['name'],
                child['birth'],
                child['comment'],
                child['parrent_name'],
                child['parrent_phone'],
            ]
        )

    doc = docx.Document(f'{current_directory}/templates/grouplist.docx')
    table = doc.tables[0]

    for i in range(len(data)):
        row = table.add_row()

        for j, value in enumerate(data[i]):
            cell = row.cells[j]
            cell_text = cell.paragraphs[0]
            run = cell_text.add_run(str(value))
            font = run.font
            font.name = "Geologica Light"
            if j != 2:  # не выравнивается ячейка с особенностями
                cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    doc.save(f"{current_directory}/generated/{filename}.docx")
    insert_metrics(filename, group_num)
    convert_to_pdf(filename)

    return filename
