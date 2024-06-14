from flet import Page, AlertDialog, Row, Container, TextButton, Text, FontWeight, MainAxisAlignment, ProgressBar, Column, CrossAxisAlignment, BottomSheet as bs, ScrollMode


class InfoDialog:
    def __init__(self, page: Page):
        self.dialog = AlertDialog(
            modal=True,
            actions_alignment=MainAxisAlignment.END,
            actions=[
                TextButton(
                    text="OK",
                    on_click=lambda _: self.close()
                )
            ]
        )
        self.content = Row(
            [
                Container(Text("Information text", size=20, weight=FontWeight.W_400), expand=True),
            ]
        )
        self.title = "Inforamtion"
        self.page = page

    def open(self, action_btn_visible: bool = True):
        self.dialog.title = Row(
            [
                Container(Text(self.title, size=20, weight=FontWeight.W_400), expand=True),
            ]
        )

        self.dialog.content = self.content

        self.page.dialog = self.dialog
        self.dialog.open = True
        self.dialog.actions[0].visible = action_btn_visible
        self.page.update()

    def close(self):
        self.dialog.open = False
        self.page.update()


class LoadingDialog:
    def __init__(self, page: Page):
        self.dialog = AlertDialog(
            modal=True
        )
        self.loading_text = "Загрузка"
        self.page = page

    def open(self):
        self.dialog.content = Column(
            controls=[
                Column(
                    [
                        Text(self.loading_text, size=20, weight=FontWeight.W_400),
                        ProgressBar()
                    ],
                    alignment=MainAxisAlignment.CENTER),
            ],
            alignment=MainAxisAlignment.CENTER,
            horizontal_alignment=CrossAxisAlignment.CENTER,
            width=400,
            height=50
        )

        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()

    def close(self):
        self.dialog.open = False
        self.page.update()


class BottomSheet:
    def __init__(self, page: Page):
        self.sheet = bs(
            show_drag_handle=True,
            is_scroll_controlled=True
        )
        self.content = None
        self.title = None
        self.page = page
        self.height = 500

    def open(self):
        self.sheet.content = Container(
            Column(
                controls=[
                    # Text(self.title, size=20, weight=FontWeight.W_400),
                    self.content
                ],
                height=self.height,
                width=800,
                scroll=ScrollMode.AUTO
            ),
            padding=15
        )
        self.page.bottom_sheet = self.sheet
        self.sheet.open = True
        self.page.update()

    def close(self):
        self.sheet.open = False
        self.page.update()