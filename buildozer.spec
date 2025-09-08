import kivy
kivy.require('2.3.0')

from kivy.app import App
from kivy.uix.label import Label
from kivy.core.window import Window
Window.clearcolor = (1, 1, 1, 1)

class DualClocksApp(App):
    def build(self):
        return Label(text='Hello from Kivy!')

if __name__ == '__main__':
    DualClocksApp().run()
