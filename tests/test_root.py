import pytest
from playwright.sync_api import Page, expect


class TestJoinRoomForm:

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        page.goto("/")
        self.page = page
        self.room_code = self.page.get_by_label("Kód místnosti:")
        self.join_button = self.page.get_by_role("button", name="Připojit se")
        self.invalid_room_code = self.page.get_by_text("Neplatný kód")

    def test_join_room(self):
        self.room_code.fill("123-456")
        self.join_button.click()
        expect(self.page).to_have_url("/play/123-456")

    def test_invalid_room_code(self):
        self.room_code.fill("xyz")
        self.join_button.click()
        expect(self.page).to_have_url("/")
        expect(self.invalid_room_code).to_be_visible()

    def test_empty_room_code(self):
        self.room_code.fill("")
        self.join_button.click()
        expect(self.page).to_have_url("/")
        expect(self.invalid_room_code).not_to_be_visible()
        expect(self.room_code).to_have_value("")
