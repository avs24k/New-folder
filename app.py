from kivy.app import App
from kivy.uix.label import Label


class MDMApp(App):
    def build(self):
        self._start_service()
        return Label(text="MDM Agent Active")

    def _start_service(self):
        from android import AndroidService

        service = AndroidService("MDM Agent", "Management service active")
        service.start("start")


if __name__ == "__main__":
    MDMApp().run()
