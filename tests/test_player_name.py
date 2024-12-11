import re

import pytest
from playwright.sync_api import BrowserContext, Page, expect


class PlayPage:
    def __init__(self, page: Page):
        page.goto("/play/1234")
        self.page = page
        self.player_name = self.page.get_by_label("Zadej svoji přezdívku:")
        self.enter_button = self.page.get_by_role("button", name="Vstoupit")
        self.wait_for_game_to_start = self.page.get_by_text(re.compile(r"Ahoj .*, počkej, než začne hra"))


class TestSetPlayerNameForm:

    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        self.page = PlayPage(page)
        self.other_page = PlayPage(page.context.new_page())

    def test_empty_player_name(self):
        self.page.enter_button.click()
        expect(self.page.player_name).to_be_visible()

    def test_set_player_name(self):
        self.page.player_name.fill("Alice")
        self.page.enter_button.click()

        expect(self.page.wait_for_game_to_start).to_contain_text("Alice")
        expect(self.other_page.wait_for_game_to_start).to_contain_text("Alice")

        p3 = PlayPage(self.page.page.context.new_page())
        expect(p3.wait_for_game_to_start).to_contain_text("Alice")


class Room:
    def __init__(self, page: Page):
        self.page = page


@pytest.fixture
def room(context: BrowserContext) -> Room:
    page = context.new_page()
    page.goto("/login")
    page.fill("input[name=username]", "admin")
    page.fill("input[name=password]", "heslo")
    page.get_by_role("button", name="Přihlásit se").click()
    page.goto("/room/1234")
    return Room(page)


def test_player_reject_name(page: Page, room: Room):
    expect(room.page.get_by_text("Alice")).not_to_be_visible()
    play = PlayPage(page)
    play.player_name.fill("Alice")
    play.enter_button.click()
    expect(room.page.get_by_text("Alice")).to_be_visible()
    expect(play.player_name).not_to_be_visible()
    r = room.page.get_by_text("Alice").locator("a", has_text="❌")
    expect(r).to_be_visible()
    r.click()
    expect(play.player_name).to_be_visible()
    expect(room.page.get_by_text("Alice")).not_to_be_visible()


def test_player_disconnect(page: Page, room: Room):
    play = PlayPage(page)
    play.player_name.fill("Alice")
    play.enter_button.click()
    expect(room.page.get_by_text("Alice")).to_be_visible()
    expect(play.player_name).not_to_be_visible()
    page.goto("/")
    expect(room.page.get_by_text("Alice")).not_to_be_visible()
