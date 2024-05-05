import os
import platform
import shutil

import docx
import groupdocs_conversion_cloud
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import Pt
from docxtpl import DocxTemplate
from datetime import datetime

current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(current_directory)


# to-do:
# Заменить конвертирование pdf на другой модуль

def insert_metrics(filepath, group_num):
    doc = DocxTemplate(f"{current_directory}/generated/{filepath}.docx")
    context = {"group_num": group_num,
               "create_time": datetime.now().strftime("%d.%m.%Y в %H:%M"),
               }
    doc.render(context)
    doc.save(f"{current_directory}/generated/{filepath}.docx")


def convert_to_pdf(filepath: str):
    docx_file = f"{current_directory}/generated/{filepath}.docx"

    configuration = groupdocs_conversion_cloud.Configuration(os.getenv('GROUPDOCS_CLIENT_ID'), os.getenv('GROUPDOCS_SECRET_ID'))
    configuration.api_base_url = "https://api.groupdocs.cloud"
    my_storage = ""

    file_api = groupdocs_conversion_cloud.FileApi.from_config(configuration)
    request = groupdocs_conversion_cloud.UploadFileRequest(f"{filepath}.docx", docx_file, my_storage)
    file_api.upload_file(request)

    convert_api = groupdocs_conversion_cloud.ConvertApi.from_keys(os.getenv('GROUPDOCS_CLIENT_ID'), os.getenv('GROUPDOCS_SECRET_ID'))

    settings = groupdocs_conversion_cloud.ConvertSettings()
    settings.file_path = f"{filepath}.docx"
    settings.format = "pdf"
    settings.output_path = ""

    request = groupdocs_conversion_cloud.ConvertDocumentRequest(settings)
    convert_api.convert_document(request)

    file_api = groupdocs_conversion_cloud.FileApi.from_config(configuration)
    request = groupdocs_conversion_cloud.DownloadFileRequest(f"{filepath}.pdf", my_storage)
    response = file_api.download_file(request)
    print(response)
    print(f"{current_directory}/generated")

    shutil.move(response, f"{current_directory}/generated")
    print(os.listdir(f"{current_directory}/generated"))

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
            font.name = "Geologica Light"
            if j != 2:  # не выравнивается ячейка с особенностями
                cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    doc.save(f"{current_directory}/generated/{filename}.docx")
    insert_metrics(filename, group_num)
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
    font.name = "Geologica"
    font.bold = True

    paragraph_body = doc.add_paragraph()
    run = paragraph_body.add_run(main_text)
    font = run.font
    font.size = Pt(13)
    font.name = "Geologica"

    doc.save(f"{current_directory}/generated/{filename}.docx")
    convert_to_pdf(filename)

    return filename
