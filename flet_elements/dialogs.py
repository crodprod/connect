from flet import Page, AlertDialog, Row, Container, TextButton, Text, FontWeight, MainAxisAlignment, ProgressBar, Column, CrossAxisAlignment


class InfoDialog:
    def __init__(self, title: str, content, page: Page):
        self.dialog = AlertDialog(
            modal=True,
            title=Row(
                [
                    Container(Text(title, size=20, weight=FontWeight.W_400), expand=True),
                ]
            ),
            content=content,
            actions_alignment=MainAxisAlignment.END,
            actions=[
                TextButton(
                    text="OK",
                    on_click=lambda _: self.close()
                )
            ]
        )
        self.title = title
        self.content = content
        self.page = page

    def open(self, action_btn_visible: bool = True):
        self.dialog.title.controls[0].content.value = self.title
        self.dialog.content = self.content

        self.page.dialog = self.dialog
        self.dialog.open = True
        self.dialog.actions[0].visible = action_btn_visible
        self.page.update()

    def close(self):
        self.dialog.open = False
        self.page.update()


class LoadingDialog:
    def __init__(self, loading_text: str = "Загрузка", page: Page = None):
        self.dialog = AlertDialog(
            modal=True,
            content=Column(
                controls=[
                    Column(
                        [
                            Text(loading_text, size=20, weight=FontWeight.W_400),
                            ProgressBar()
                        ],
                        alignment=MainAxisAlignment.CENTER),
                ],
                alignment=MainAxisAlignment.CENTER,
                horizontal_alignment=CrossAxisAlignment.CENTER,
                width=400,
                height=50
            )
        )
        self.loading_text = loading_text
        self.page = page

    def open(self):
        self.dialog.content.controls[0].controls[0].value = self.loading_text
        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()

    def close(self):
        self.dialog.open = False
        self.page.update()
