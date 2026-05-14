from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Input, OptionList, Button, Label
from textual import on, events
from textual.message import Message
from textual.screen import ModalScreen

class ConfirmModal(ModalScreen[bool]):
    """A modal dialog that asks a Yes/No question."""
    def __init__(self, message: str, yes_text: str = "Yes", no_text: str = "No", id: str = None):
        super().__init__(id=id)
        self.message = message
        self.yes_text = yes_text
        self.no_text = no_text

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm_dialog"):
            yield Label(self.message, id="confirm_message")
            with Horizontal(id="confirm_buttons"):
                yield Button(self.yes_text, variant="error", id="btn_yes")
                yield Button(self.no_text, variant="primary", id="btn_no")

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

class SelectModal(ModalScreen[int]):
    """A modal dialog that asks the user to select an option."""
    def __init__(self, title: str, options: list[str], id: str = None):
        super().__init__(id=id)
        self.title = title
        self.options = options

    def compose(self) -> ComposeResult:
        with Vertical(id="select_dialog"):
            yield Label(self.title, id="select_title")
            yield OptionList(*self.options, id="select_list")
            with Horizontal(id="select_buttons"):
                yield Button("Cancel", variant="error", id="btn_cancel")

    @on(OptionList.OptionSelected, "#select_list")
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option_index)

    @on(Button.Pressed, "#btn_cancel")
    def on_cancel(self, event: Button.Pressed) -> None:
        self.dismiss(None)

class SearchableSelect(Vertical):
    """A custom filterable combobox widget."""
    
    class Changed(Message):
        def __init__(self, value: str, select: "SearchableSelect"):
            self.value = value
            self.select = select
            super().__init__()
            
        @property
        def control(self):
            return self.select
            
    def __init__(self, prompt: str = "Search...", id: str = None):
        super().__init__(id=id)
        self.prompt = prompt
        self._options = []
        self._current_value = ""
        self._selecting = False

    def compose(self) -> ComposeResult:
        yield Input(placeholder=self.prompt, id="search_input")
        yield OptionList(id="search_options", classes="hidden")
        
    def set_options(self, options: list[tuple[str, str] | str]):
        self._options = []
        for opt in options:
            if isinstance(opt, tuple):
                self._options.append((str(opt[0]), str(opt[1])))
            else:
                self._options.append((str(opt), str(opt)))
        
        self._repopulate_options()
            
    def _repopulate_options(self, filter_term: str = ""):
        opt_list = self.query_one("#search_options", OptionList)
        opt_list.clear_options()
        
        has_matches = False
        for label, val in self._options:
            if not filter_term or filter_term in label.lower() or filter_term in val.lower():
                opt_list.add_option(label)
                has_matches = True
                
        return has_matches
            
    @property
    def value(self) -> str:
        return self._current_value
        
    @value.setter
    def value(self, new_value: str):
        self._current_value = new_value
        label = new_value
        for l, v in self._options:
            if v == new_value:
                label = l
                break
                
        inp = self.query_one("#search_input", Input)
        with inp.prevent(Input.Changed):
            inp.value = label
            
        self.post_message(self.Changed(new_value, self))
        
    @on(Input.Changed, "#search_input")
    def on_input_changed(self, event: Input.Changed):
        if self._selecting:
            self._selecting = False
            return
            
        opt_list = self.query_one("#search_options", OptionList)
        search_term = event.value.lower()
        
        has_matches = self._repopulate_options(search_term)
                
        if has_matches:
            opt_list.remove_class("hidden")
            opt_list.add_class("visible")
        else:
            opt_list.remove_class("visible")
            opt_list.add_class("hidden")
            
        if not event.value:
            self._current_value = ""
            self.post_message(self.Changed("", self))

    @on(events.Click, "#search_input")
    def on_input_clicked(self, event: events.Click):
        opt_list = self.query_one("#search_options", OptionList)
        inp = self.query_one("#search_input", Input)
        has_matches = self._repopulate_options(inp.value.lower())
        if has_matches:
            opt_list.remove_class("hidden")
            opt_list.add_class("visible")

    @on(Input.Submitted, "#search_input")
    def on_input_submitted(self, event: Input.Submitted):
        # If they press enter, maybe focus the list or select first
        pass
            
    @on(OptionList.OptionSelected, "#search_options")
    def on_option_selected(self, event: OptionList.OptionSelected):
        label = str(event.option.prompt)
        val = label
        for l, v in self._options:
            if l == label:
                val = v
                break
                
        self._current_value = val
        self._selecting = True
        
        inp = self.query_one("#search_input", Input)
        inp.value = label
            
        opt_list = self.query_one("#search_options", OptionList)
        opt_list.remove_class("visible")
        opt_list.add_class("hidden")
        
        self.post_message(self.Changed(val, self))

    def focus_input(self):
        self.query_one("#search_input", Input).focus()
