import math
import os
import platform
import shutil

import docx
# import groupdocs_conversion_cloud
import convertapi
import qrcode
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import Pt, Inches
from docxtpl import DocxTemplate
from datetime import datetime

current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(current_directory)


# to-do:
# Заменить конвертирование pdf на другой модуль

groups_dict = {
    "children": "Дети",
    "admins": "Администрация",
    "mentors": "Воспитатели",
    "teachers": "Преподаватели"
}

def insert_metrics(filepath, group_num):
    doc = DocxTemplate(f"{current_directory}/generated/{filepath}.docx")
    context = {"group_num": group_num,
               "create_time": datetime.now().strftime("%d.%m.%Y в %H:%M"),
               }
    doc.render(context)
    doc.save(f"{current_directory}/generated/{filepath}.docx")


def convert_to_pdf(filepath: str):
    convertapi.api_secret = os.getenv('CONVERT_SECRET')
    docx_file = f"{current_directory}/generated/{filepath}.docx"

    converted = convertapi.convert(
        'pdf',
        {
            'File': docx_file
        },
        from_format='doc'
    )
    converted.save_files(f"{current_directory}/generated")

    if os.path.exists(docx_file):
        os.remove(docx_file)


def get_grouplist(group_list: [], group_num: int):
    filename = f"grouplist_{group_num}_{datetime.now().date().strftime('%d%m%Y')}"
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
            font.name = "Arial Light"
            if j != 2:  # не выравнивается ячейка с особенностями
                cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    doc.save(f"{current_directory}/generated/{filename}.docx")
    insert_metrics(filename, group_num)
    convert_to_pdf(filename)

    return filename


def get_qr_list(group: str, group_list: [], value: str = ""):
    if value:
        extra = f"_{value}"
    else:
        extra = ""
    filename = f"qrlist_{group}{extra}_{datetime.now().date().strftime('%d%m%Y')}"
    doc = docx.Document(f'{current_directory}/templates/qr_table.docx')

    group_list.sort(key=lambda user: user['name'])
    for user in group_list:
        print(f"creating qr {user['pass_phrase']}")
        qr_img = qrcode.make(f"https://t.me/crod_connect_bot?start={group}_{user['pass_phrase']}")
        qr_img.save(f"{current_directory}/qr/{user['pass_phrase']}.png")
        print('OK')
    users_count = len(group_list)
    rows, cols = math.ceil(users_count / 4), 4
    qr_table = doc.add_table(rows, cols)

    sections = doc.sections
    for section in sections:
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)

    index = 0
    for row in range(rows):
        for col in range(cols):
            if index + 1 <= users_count:
                cell = qr_table.cell(row, col)
                cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                paragraph = cell.paragraphs[0]
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                name = " ".join(group_list[index]['name'].split(" ")[:2])
                paragraph.add_run().add_text(name)
                paragraph.runs[-1].font.size = Pt(11)
                paragraph.runs[-1].font.name = "Arial"

                image_path = f"{current_directory}/qr/{group_list[index]['pass_phrase']}.png"
                paragraph.add_run().add_picture(image_path, width=Inches(1.7))
                index += 1

    doc.save(f"{current_directory}/generated/{filename}.docx")
    if value:
        insert_metrics(filename, f"№{value}")
    else:
        insert_metrics(filename, groups_dict[group])
    convert_to_pdf(filename)

    return filename


def get_feedback(module_name: str, feedback_list: []):
    creation_date = datetime.now().date().strftime('%d_%m_%Y')
    filename = f"feedback_{module_name}_{creation_date}"
    doc = docx.Document(f'{current_directory}/templates/feedback.docx')

    title = f"Обратная связь по модулю «{module_name}» за {creation_date}"
    main_text = ""

    for fb in feedback_list:
        main_text += f"Оценка: {fb['mark']}\nКомментарий: {fb['comment']}\n\n"

    paragraph_title = doc.add_paragraph()
    run = paragraph_title.add_run(title)
    font = run.font
    font.size = Pt(15)
    font.name = "Arial"
    font.bold = True

    paragraph_body = doc.add_paragraph()
    run = paragraph_body.add_run(main_text)
    font = run.font
    font.size = Pt(13)
    font.name = "Arial"

    doc.save(f"{current_directory}/generated/{filename}.docx")
    convert_to_pdf(filename)

    return filename
