from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

class MyRoot(BoxLayout):
    pass

class MyApp(App):
    def build(self):
        root = BoxLayout(orientation="vertical", padding=20, spacing=10)
        root.add_widget(Label(text="Hello from Android APK!", font_size="24sp"))
        root.add_widget(Label(text="Replace main.py with your Kivy app code.", font_size="16sp"))
        return root

if __name__ == "__main__":
    MyApp().run()
