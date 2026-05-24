# -*- coding: utf-8 -*-
# ZaVr2 Match App - Pythonista (English)
# Version: 1.0.3
# Place match.yaml in the same folder as this script

APP_VERSION = '1.0.3'

import collections
import collections.abc
collections.Hashable        = collections.abc.Hashable
collections.Mapping         = collections.abc.Mapping
collections.MutableMapping  = collections.abc.MutableMapping
collections.Callable        = collections.abc.Callable

import ui
import time
import threading
import yaml
import os
from objc_util import on_main_thread
from datetime import datetime

# ---------------------------------------------------------------------------
# Emoji lookup
# ---------------------------------------------------------------------------
EVENT_ICONS = {
    'Goal':       '\u26bd',
    'Substitution':'\U0001f504',
    'Yellow card': '\U0001f7e8',
    'Red card':    '\U0001f7e5',
    'Shot':        '\U0001f3af',
    'Corner':      '\U0001f6a9',
    'Free kick':   '\U0001f9b6',
    'Offside':     '\U0001f6ab',
    'Foul':        '\u270b',
    'Penalty':    '\U0001f4a5',
    'Throw-in':    '\U0001f44c',
    'Goal kick':   '\U0001f91a',
}

def get_icon(name):
    return EVENT_ICONS.get(name, '\u25b6')

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
CLR_HOME_STARTER   = '#2980b9'
CLR_HOME_SUB  = '#1a4f72'
CLR_AWAY_STARTER     = '#c0392b'
CLR_AWAY_SUB    = '#6b1f17'
CLR_EVENT_IDLE    = '#5d3a7a'
CLR_EVENT_ACTIVE  = '#8e44ad'
CLR_EVENT_SEL     = '#f1c40f'
CLR_BG            = '#1e1e2e'
CLR_PANEL         = '#2d2d3f'
CLR_RED_CARD    = '#7f0000'   # uitgesloten player

# ---------------------------------------------------------------------------
# Load YAML
# ---------------------------------------------------------------------------
YAML_PATH = 'match.yaml'

DEMO_YAML = """
match:
  date: 2026-05-17
  home: ZaVr2
  away: Ajax VR3

home:
  - name: Lisa
    number: 1
  - name: Sara
    number: 4
  - name: Dane
    number: 7
  - name: Fatima
    number: 9
  - name: Roos
    number: 11
  - name: Mila
    number: 3
  - name: Jade
    number: 6
  - name: Nina
    number: 10
  - name: Eva
    number: 14
  - name: Kim
    number: 2
  - name: Lotte
    number: 5
  - name: Britt
    number: 8
  - name: Anouk
    number: 15
  - name: Fleur
    number: 17

away:
  - name: Emma
    number: 2
  - name: Julia
    number: 5
  - name: Noor
    number: 8
  - name: Lena
    number: 3
  - name: Hanna
    number: 7
  - name: Vera
    number: 11
  - name: Sofie
    number: 1
  - name: Inge
    number: 6
  - name: Petra
    number: 9
  - name: Rosa
    number: 13
  - name: Tara
    number: 16

events:
  - name: Goal
    extra: assist
  - name: Substitution
    extra: substitution
  - name: Yellow card
    extra: reason
  - name: Red card
    extra: reason
  - name: Shot
    extra: result
  - name: Corner
    extra: none
  - name: Free kick
    extra: none
  - name: Offside
    extra: none
  - name: Foul
    extra: none
  - name: Penalty
    extra: result
  - name: Throw-in
    extra: none
  - name: Goal kick
    extra: none
"""

def load_match_data():
    if os.path.exists(YAML_PATH):
        with open(YAML_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return yaml.safe_load(DEMO_YAML)

data = load_match_data()

# ---------------------------------------------------------------------------
# App state
# ---------------------------------------------------------------------------
class AppState:
    def __init__(self):
        self.match_started      = False
        self.running            = False
        self.start_time         = 0.0
        self.elapsed            = 0.0
        self.timer_thread       = None
        self.selected_event     = None
        self.selected_event_btn = None
        self.event_time         = None   # time captured at moment of event tap
        self.event_log          = []
        self.score_home         = 0
        self.score_away         = 0
        # name -> 'starter' | 'sub' | None
        self.status = {
            'home': {p['name']: None for p in data.get('home', [])},
            'away': {p['name']: None for p in data.get('away', [])},
        }
        self.suspended   = set()   # players with red card

        self.period      = None    # 1, 2, 3, 4 or None



        self.period_dur  = 45 * 60 # seconds per regular period


    def starters(self, team):
        return [n for n, s in self.status[team].items()
                if s == 'starter' and n not in self.suspended]

    def subs(self, team):
        return [n for n, s in self.status[team].items()
                if s == 'sub' and n not in self.suspended]

    def starter_count(self, team):
        return sum(1 for n, s in self.status[team].items()
                   if s == 'starter' and n not in self.suspended)

state = AppState()

# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------
def current_elapsed():
    return int(state.elapsed + (time.time() - state.start_time if state.running else 0))

def format_time(seconds):
    return f'{seconds // 60:02d}:{seconds % 60:02d}'

def format_time_log():
    """Time for log output: P1 | 45:00+02:30 if over period duration."""
    sec   = current_elapsed()
    pdur  = state.period_dur
    p     = state.period or '?'
    if sec > pdur:



        return f'P{p} | {format_time(pdur)}+{format_time(sec - pdur)}'
    return f'P{p} | {format_time(sec)}'

def format_display():
    """Time for the clock display, showing extra time if applicable."""
    sec   = current_elapsed()
    pdur  = state.period_dur
    if state.period and sec > pdur:
        extra = sec - pduur
        return f'{format_time(pduur)}+{format_time(extra)}'
    return format_time(sec)

# ---------------------------------------------------------------------------
# Clock
# ---------------------------------------------------------------------------
@on_main_thread
def set_display_text(text):
    main_view['display'].text = text

def update_display():
    set_display_text(format_display())

def _tick():
    while state.running:
        update_display()
        time.sleep(0.5)

def start_clock():
    state.start_time   = time.time()
    state.running      = True
    state.timer_thread = threading.Thread(target=_tick, daemon=True)
    state.timer_thread.start()

# ---------------------------------------------------------------------------
# Button B helpers
# ---------------------------------------------------------------------------
@on_main_thread
def update_end_btn():
    """Update label of Button B based on current period."""
    btn = main_view['end_btn']
    if btn is None:
        return
    p = state.period
    if p is None:
        btn.title   = 'End Period 1'
        btn.enabled = False
        btn.background_color = '#555555'
    elif p < 2:
        btn.title   = f'End Period {p}'
        btn.enabled = True
        btn.background_color = '#c0392b'
    else:
        btn.title   = 'End match'
        btn.enabled = True
        btn.background_color = '#8e0000'

def tapped_end(sender):
    """Button B: End Period x or End Match."""
    p = state.period
    if p is None:
        return

    # After period 2 (or 4 in extra time): always show end match popup
    is_end_match    = (p == 4)
    # After period 2: ask end match or extra time
    is_after_normal = (p == 2)

    pw  = 340
    ph  = 240 if (is_end_match or is_after_normal) else 150
    confirm                  = ui.View()
    confirm.background_color = CLR_PANEL
    confirm.corner_radius    = 12
    confirm.frame            = (0, 0, pw, ph)

    # Titeltekst
    if is_end_match:
        question = 'End of match?'
    elif is_after_normal:
        question = f'End of Period {p}\nEnd match or extra time?'
    else:
        question = f'End of Period {p}?\nTimer resets to 00:00.'

    lbl                 = ui.Label()
    lbl.frame           = (12, 14, pw - 24, 50)
    lbl.text            = question
    lbl.font            = ('<system-bold>', 15)
    lbl.text_color      = 'white'
    lbl.alignment       = ui.ALIGN_CENTER
    lbl.number_of_lines = 2
    confirm.add_subview(lbl)

    btn_w = (pw - 36) // 2
    y1    = 76
    y2    = y1 + 50

    def make_popup_btn(title, x, y, w, color, action):
        b                  = ui.Button(title=title)
        b.frame            = (x, y, w, 40)
        b.background_color = color
        b.tint_color       = 'white'
        b.corner_radius    = 8
        b.font             = ('<system-bold>', 13)
        b.action           = action
        confirm.add_subview(b)

    cancel = lambda s: confirm.close()

    if is_end_match:
        # Save/close options only
        def save_and_close(s):
            do_save()
            do_reset_timer()
            confirm.close()
        def close_only(s):
            do_reset_timer()
            confirm.close()
        make_popup_btn('Save & close',        12,  y1, btn_w, '#27ae60', save_and_close)
        make_popup_btn('Cancel',              24+btn_w, y1, btn_w, '#7f8c8d', cancel)
        make_popup_btn('Close without saving',12,  y2, pw-24, '#c0392b', close_only)

    elif is_after_normal:
        # End match or extra time (P3)
        def end_match(s):
            show_end_match_popup()
            confirm.close()
        def extra_time(s):
            do_end_period()
            # Knop B wordt Einde Periode 3, wacht op Start
            confirm.close()
        maak_btn_popup('End match',  12,       y1, btn_w, '#8e0000', einde_wedstrijd)
        make_popup_btn('Extra time (P3)', 24+btn_w, y1, btn_w, '#2980b9', extra_time)
        maak_btn_popup('Cancel',         12,       y2, pw-24, '#7f8c8d', ann)

    else:
        # Periode 1 of 3: gewoon bevestigen
        def ok_end(s):
            do_end_period()
            confirm.close()
        maak_btn_popup(f'OK, end P{p}', 12,       y1, btn_w, '#c0392b', ok_einde)
        make_popup_btn('Cancel',         24+btn_w, y1, btn_w, '#7f8c8d', cancel)

    confirm.present('popover')

def show_end_match_popup():
    """Save/close popup after end of match."""
    pw, ph = 340, 190
    popup                  = ui.View()
    popup.background_color = CLR_PANEL
    popup.corner_radius    = 12
    popup.frame            = (0, 0, pw, ph)

    lbl            = ui.Label()
    lbl.frame      = (12, 14, pw - 24, 32)
    lbl.text       = 'Match finished!'
    lbl.font       = ('<system-bold>', 16)
    lbl.text_color = 'white'
    lbl.alignment  = ui.ALIGN_CENTER
    popup.add_subview(lbl)

    btn_w = (pw - 36) // 2

    def save_and_close(s):
        do_save()
        do_reset_timer()
        popup.close()

    def close_only(s):
        do_reset_timer()
        popup.close()

    def maak_b(title, x, y, w, color, action):
        b                  = ui.Button(title=title)
        b.frame            = (x, y, w, 40)
        b.background_color = color
        b.tint_color       = 'white'
        b.corner_radius    = 8
        b.font             = ('<system-bold>', 13)
        b.action           = action
        popup.add_subview(b)

    maak_b('Save & close',       12,       62, btn_w, '#27ae60', save_and_close)
    maak_b('Cancel',             24+btn_w, 62, btn_w, '#7f8c8d', lambda s: popup.close())
    maak_b('Close without saving', 12,      112, pw-24, '#c0392b', zonder)

    popup.present('popover')

def do_end_period():
    """Reset timer after period end, Button A back to Start, Button B to next period (disabled)."""
    if state.running:
        state.elapsed += time.time() - state.start_time
        state.running  = False
    state.elapsed = 0.0
    set_display_text('00:00')
    set_events_enabled(False)
    deselect_event()
    btn_a                  = main_view['start_pause_btn']
    btn_a.title            = 'Start'
    btn_a.background_color = '#27ae60'
    btn_a.action           = tapped_start
    # Button B: next period, disabled until Start
    btn_b                  = main_view['end_btn']
    next_period            = state.period + 1
    btn_b.title            = f'End Period {next_period}'
    btn_b.enabled          = False
    btn_b.background_color = '#555555'

def do_reset_timer():
    """Fully close match: stop timer, disable all buttons."""
    if state.running:
        state.elapsed += time.time() - state.start_time
        state.running  = False
    state.elapsed = 0.0
    set_display_text('00:00')
    set_events_enabled(False)
    deselect_event()
    btn_a                  = main_view['start_pause_btn']
    btn_a.title            = 'Start'
    btn_a.background_color = '#555555'
    btn_a.enabled          = False
    btn_b                  = main_view['end_btn']
    btn_b.title            = 'End match'
    btn_b.enabled          = False
    btn_b.background_color = '#555555'

def do_save():
    """Sla match op als YAML met vaste veldvolgorde."""
    FIELD_ORDER = ['time', 'event', 'own_goal', 'icon', 'player', 'team', 'extra']

    def order_entry(entry):
        return {k: entry[k] for k in FIELD_ORDER if k in entry}

    output = {
        'match':  data.get('match', {}),
        'events': [order_entry(e) for e in state.event_log],
    }
    filename = f'match_{datetime.now().strftime("%Y%m%d_%H%M")}.yaml'

    # Write with fixed field order via custom Dumper
    class OrderedDumper(yaml.Dumper):
        pass
    OrderedDumper.add_representer(
        dict,
        lambda d, data: d.represent_mapping(
            'tag:yaml.org,2002:map', data.items()))

    with open(filename, 'w', encoding='utf-8') as f:
        yaml.dump(output, f, Dumper=OrderedDumper,
                  allow_unicode=True, default_flow_style=False)
    print(f'Saved as {filename}')

# ---------------------------------------------------------------------------
# Button A: Start / Pause / Resume
# ---------------------------------------------------------------------------
def tapped_start(sender):
    """First start: ask which period."""
    if not state.match_started:
        return
    show_period_popup(sender)

def show_period_popup(start_btn):
    pw, ph = 300, 180
    popup                  = ui.View()
    popup.background_color = CLR_PANEL
    popup.corner_radius    = 12
    popup.frame            = (0, 0, pw, ph)

    lbl            = ui.Label()
    lbl.frame      = (12, 12, pw - 24, 28)
    lbl.text       = 'Which period?'
    lbl.font       = ('<system-bold>', 16)
    lbl.text_color = 'white'
    lbl.alignment  = ui.ALIGN_CENTER
    popup.add_subview(lbl)

    btn_w = (pw - 5 * 10) // 4
    for i, p in enumerate([1, 2, 3, 4]):
        pb              = ui.Button(title=str(p))
        pb.frame        = (10 + i * (btn_w + 10), 52, btn_w, 48)
        pb.background_color = CLR_HOME_STARTER
        pb.tint_color   = 'white'
        pb.corner_radius = 8
        pb.font         = ('<system-bold>', 20)
        def make_period_handler(period, sb=start_btn):
            def handler(s):
                state.period = period
                set_events_enabled(True)
                start_clock()
                sb.title            = 'Pause'
                sb.background_color = '#e67e22'
                sb.action           = tapped_pause
                # Knop B activeren
                btn_b = main_view['end_btn']
                if btn_b:
                    btn_b.title   = f'End Period {period}'
                    btn_b.enabled = True
                    # P4 = last extra time period = dark red, otherwise red
                    btn_b.background_color = '#8e0000' if period == 4 else '#c0392b'
                update_display()
                popup.close()
            return handler
        pb.action = make_period_handler(p)
        popup.add_subview(pb)

    ann              = ui.Button(title='Cancel')
    ann.frame        = (10, 112, pw - 20, 40)
    ann.background_color = '#7f8c8d'
    ann.tint_color   = 'white'
    ann.corner_radius = 8
    ann.font         = ('<system-bold>', 14)
    ann.action       = lambda s: popup.close()
    popup.add_subview(ann)

    popup.present('popover')

def tapped_pause(sender):
    """Pause / Resume."""
    if state.running:
        state.elapsed          += time.time() - state.start_time
        state.running           = False
        sender.title            = 'Resume'
        sender.background_color = '#27ae60'
    else:
        start_clock()
        sender.title            = 'Pause'
        sender.background_color = '#e67e22'

def tapped_stop(sender):
    """No longer used, kept for compatibility."""
    if state.running:
        state.elapsed += time.time() - state.start_time
        state.running  = False
        update_display()
    btn = main_view['start_pause_btn']
    btn.title            = 'Resume'
    btn.background_color = '#27ae60'
    btn.action           = tapped_pause

def tapped_reset(sender):
    """Reset — alleen als klok in pauze staat."""
    if state.running:
        # Clock display loopt nog: flash melding
        orig = sender.title
        sender.title            = 'Stop first!'
        sender.background_color = '#e74c3c'
        def restore():
            time.sleep(1.2)
            reset_reset_btn(sender, orig)
        threading.Thread(target=herstel, daemon=True).start()
        return
    confirm = ui.View()
    confirm.background_color = CLR_PANEL
    confirm.corner_radius    = 12
    confirm.frame            = (0, 0, 320, 140)

    lbl            = ui.Label()
    lbl.frame      = (12, 16, 296, 44)
    lbl.text       = 'Reset match?\nAll data will be lost.'
    lbl.font       = ('<system-bold>', 15)
    lbl.text_color = 'white'
    lbl.alignment  = ui.ALIGN_CENTER
    lbl.number_of_lines = 2
    confirm.add_subview(lbl)

    btn_w = 130

    def do_reset(s):
        state.running  = False
        state.elapsed  = 0.0
        state.event_log.clear()
        state.score_home = 0
        state.score_away   = 0
        state.suspended.clear()
        for team in state.status:
            for name in state.status[team]:
                state.status[team][name] = None
        state.period       = None
        state.match_started = False
        set_display_text('00:00')
        update_score()
        refresh_log()
        deselect_event()
        set_events_enabled(False)
        btn_sp                  = main_view['start_pause_btn']
        btn_sp.title            = 'Start'
        btn_sp.background_color = '#27ae60'
        btn_sp.enabled          = False
        btn_sp.action           = tapped_start
        main_view['lineup_btn'].title            = 'Set lineup'
        main_view['lineup_btn'].background_color = '#8e44ad'
        btn_b                  = main_view['end_btn']
        btn_b.title            = 'End Period 1'
        btn_b.enabled          = False
        btn_b.background_color = '#555555'
        confirm.close()

    ja_btn              = ui.Button(title='Yes, reset')
    ja_btn.frame        = (12, 84, btn_w, 40)
    ja_btn.background_color = '#c0392b'
    ja_btn.tint_color   = 'white'
    ja_btn.corner_radius = 8
    ja_btn.font         = ('<system-bold>', 14)
    ja_btn.action       = do_reset
    confirm.add_subview(ja_btn)

    nee_btn              = ui.Button(title='Cancel')
    nee_btn.frame        = (178, 84, btn_w, 40)
    nee_btn.background_color = '#7f8c8d'
    nee_btn.tint_color   = 'white'
    nee_btn.corner_radius = 8
    nee_btn.font         = ('<system-bold>', 14)
    nee_btn.action       = lambda s: confirm.close()
    confirm.add_subview(nee_btn)

    confirm.present('popover')

@on_main_thread
def reset_reset_btn(btn, orig):
    btn.title            = orig
    btn.background_color = '#7f8c8d'

# ---------------------------------------------------------------------------
# Enable / disable event buttons
# ---------------------------------------------------------------------------
@on_main_thread
def set_events_enabled(enabled):
    for event in data.get('events', [])[:12]:
        btn = main_view[event['name']]
        if btn:
            btn.enabled          = enabled
            btn.background_color = CLR_EVENT_ACTIVE if enabled else CLR_EVENT_IDLE

# ---------------------------------------------------------------------------
# Lineup screen
# ---------------------------------------------------------------------------
def show_lineup_screen():
    pw  = min(700, int(_sw) - 10)
    ph  = 580
    panel                  = ui.View()
    panel.background_color = CLR_BG
    panel.frame            = (0, 0, pw, ph)

    titel            = ui.Label()
    titel.frame      = (12, 10, pw - 24, 32)
    titel.text       = 'Set lineup  (max 11 starters per team)'
    titel.font       = ('<system-bold>', 16)
    titel.text_color = 'white'
    titel.alignment  = ui.ALIGN_CENTER
    panel.add_subview(titel)

    col_start = {'home': 12, 'away': pw // 2 + 6}
    col_w     = pw // 2 - 18

    for team in ('home', 'away'):
        team_name = data['match'][team]
        clr_s   = CLR_HOME_STARTER  if team == 'home' else CLR_AWAY_STARTER
        clr_sub   = CLR_HOME_SUB if team == 'home' else CLR_AWAY_SUB

        lbl            = ui.Label()
        lbl.frame      = (col_start[team], 48, col_w, 24)
        lbl.text       = f'{"Home" if team == "home" else "Away"}: {team_name}'
        lbl.font       = ('<system-bold>', 14)
        lbl.text_color = clr_s
        lbl.alignment  = ui.ALIGN_CENTER
        panel.add_subview(lbl)

        counter            = ui.Label()
        counter.name       = f'counter_{team}'
        counter.frame      = (col_start[team], 74, col_w, 20)
        counter.text       = f'Starters: {state.starter_count(team)} / 11'
        counter.font       = ('<system>', 12)
        counter.text_color = '#aaaaaa'
        counter.alignment  = ui.ALIGN_CENTER
        panel.add_subview(counter)

        scroll                  = ui.ScrollView()
        scroll.frame            = (col_start[team], 98, col_w, ph - 170)
        scroll.background_color = CLR_PANEL
        scroll.corner_radius    = 8
        panel.add_subview(scroll)

        players  = data.get(team, [])
        btn_h    = 44
        btn_cols = 3
        btn_w    = (col_w - 8 - (btn_cols - 1) * 6) // btn_cols

        for idx, sp in enumerate(players[:18]):
            col = idx % btn_cols
            row = idx // btn_cols
            x   = 4 + col * (btn_w + 6)
            y   = 4 + row * (btn_h + 6)

            current = state.status[team][sp['name']]
            if current == 'starter':   clr = clr_s
            elif current == 'sub':     clr = clr_sub
            else:                      clr = '#444455'

            sb              = ui.Button(title=f'{sp["number"]} {sp["name"]}')
            sb.name         = f'lineup_{team}_{sp["name"]}'
            sb.frame        = (x, y, btn_w, btn_h)
            sb.background_color = clr
            sb.tint_color   = 'white'
            sb.corner_radius = 6
            sb.font         = ('<system>', 13)

            def make_handler(t, name, btn_ref, ctr, cs, csub):
                def handler(s):
                    current = state.status[t][name]
                    if current is None:
                        if state.starter_count(t) < 11:
                            state.status[t][name]    = 'starter'
                            btn_ref.background_color = cs
                        else:
                            state.status[t][name]    = 'sub'
                            btn_ref.background_color = csub
                    elif current == 'starter':
                        state.status[t][name]    = 'sub'
                        btn_ref.background_color = csub
                    elif current == 'sub':
                        state.status[t][name]    = None
                        btn_ref.background_color = '#444455'
                    ctr.text = f'Starters: {state.starter_count(t)} / 11'
                return handler

            sb.action = make_handler(team, sp['name'], sb, counter, clr_s, clr_sub)
            scroll.add_subview(sb)

        rows_needed         = -(-len(players[:18]) // btn_cols)
        scroll.content_size = (col_w - 8, rows_needed * (btn_h + 6) + 8)

    # Legenda
    leg            = ui.Label()
    leg.frame      = (12, ph - 66, pw - 24, 18)
    leg.text       = 'Tap: empty > Starter (bright) > Sub (dark) > empty'
    leg.font       = ('<system>', 11)
    leg.text_color = '#888888'
    leg.alignment  = ui.ALIGN_CENTER
    panel.add_subview(leg)

    # Done button — closes lineup screen, match not yet started
    def klaar(s):
        main_view['lineup_btn'].title            = 'Lineup'
        main_view['lineup_btn'].background_color = '#27ae60'
        # Activate the Start button
        btn_sp          = main_view['start_pause_btn']
        btn_sp.enabled  = True
        btn_sp.title    = 'Start'
        btn_sp.background_color = '#27ae60'
        btn_sp.action   = tapped_start
        state.match_started = True
        panel.close()

    klaar_btn              = ui.Button(title='Done')
    klaar_btn.frame        = (pw // 2 - 130, ph - 54, 260, 44)
    klaar_btn.background_color = '#27ae60'
    klaar_btn.tint_color   = 'white'
    klaar_btn.corner_radius = 10
    klaar_btn.font         = ('<system-bold>', 16)
    klaar_btn.action       = klaar
    panel.add_subview(klaar_btn)

    panel.present('sheet')

# ---------------------------------------------------------------------------
# Event selection
# ---------------------------------------------------------------------------
def deselect_event():
    if state.selected_event_btn:
        state.selected_event_btn.background_color = CLR_EVENT_ACTIVE
    state.selected_event     = None
    state.selected_event_btn = None

def tapped_event(sender):
    if not state.match_started:
        return
    if state.selected_event_btn == sender:
        deselect_event()
        return
    deselect_event()
    name       = sender.name
    event_data = next((e for e in data['events'] if e['name'] == name), None)
    if not event_data:
        return
    state.selected_event     = event_data
    state.selected_event_btn = sender
    state.event_time         = format_time_log()   # vastleggen op moment van klik
    sender.background_color  = CLR_EVENT_SEL

# ---------------------------------------------------------------------------
# Home / Away buttons
# ---------------------------------------------------------------------------
def tapped_team(sender):
    if not state.selected_event:
        flash_hint()
        return
    team = 'home' if sender.name == 'home_btn' else 'away'
    show_popup(state.selected_event, team)

@on_main_thread
def flash_hint():
    lbl = main_view['hint_label']
    if lbl:
        lbl.text_color = '#e74c3c'
    def reset():
        time.sleep(1.5)
        restore_hint()
    threading.Thread(target=reset, daemon=True).start()

@on_main_thread
def restore_hint():
    lbl = main_view['hint_label']
    if lbl:
        lbl.text_color = '#555555'

# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------
@on_main_thread
def update_score():
    main_view['score_label'].text = (
        f'{data["match"]["home"]}  {state.score_home} - '
        f'{state.score_away}  {data["match"]["away"]}'
    )

# ---------------------------------------------------------------------------
# Match log
# ---------------------------------------------------------------------------
@on_main_thread
def refresh_log():
    lines = []
    for e in reversed(state.event_log):
        team_label = ''
        if e['team'] == 'home':
            team_label = f' [{data["match"]["home"]}]'
        elif e['team'] == 'away':
            team_label = f' [{data["match"]["away"]}]'
        line  = f'{e["time"]} {e["icon"]} {e["event"]}{team_label}'
        if e.get('own_goal'):
            line += ' (OG)'
        if e['player']:
            line += f' - {e["player"]}'
        if e['extra']:
            line += f' > {e["extra"]}'
        lines.append(line)
    main_view['log_view'].text = '\n'.join(lines)

def log_event(event_data, player, team, extra, own_goal=False):
    t     = state.event_time or format_time_log()
    entry = {
        'time':     t,
        'event':    event_data['name'],
        'icon':     get_icon(event_data['name']),
        'player':     player or '',
        'team':     team or '',
        'extra':    extra or '',
        'own_goal': own_goal,
    }
    state.event_log.append(entry)

    # Score
    if event_data['name'] in ('Goal', 'Penalty'):
        if own_goal:
            if team == 'home': state.score_away   += 1
            else:               state.score_home += 1
        else:
            if team == 'home': state.score_home += 1
            elif team == 'away': state.score_away   += 1

    # Rode kaart: player uitsluiten
    if event_data['name'] == 'Red card' and player:
        state.suspended.add(player)
        # If starter: remove from starters (team now has 10)
        if player in state.status.get(team, {}):
            state.status[team][player] = None
        print(f'  {player} uitgesloten (rode kaart)')

    parts = [t, get_icon(event_data['name']), event_data['name']]
    if own_goal: parts.append('(own goal)')
    if player:   parts.append(f'({team}) {player}')
    if extra:    parts.append(f'> {extra}')
    print(' | '.join(parts))

    update_score()
    refresh_log()
    deselect_event()

# ---------------------------------------------------------------------------
# Save (do_save is defined with Button B logic above)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Player scroll list helper
# ---------------------------------------------------------------------------
def make_player_scroll(parent, players_info, x, y, w, h, geselecteerd):
    btn_cols = 2
    btn_w    = (w - 8 - (btn_cols - 1) * 6) // btn_cols
    btn_h    = 38
    rows     = max(1, -(-len(players_info) // btn_cols))

    scroll                  = ui.ScrollView()
    scroll.frame            = (x, y, w, h)
    scroll.background_color = '#1a1a2e'
    scroll.corner_radius    = 8
    parent.add_subview(scroll)

    for idx, info in enumerate(players_info):
        col = idx % btn_cols
        row = idx // btn_cols
        sb  = ui.Button(title=info['name'])
        sb.frame            = (4 + col * (btn_w + 6), 4 + row * (btn_h + 4), btn_w, btn_h)
        sb.background_color = info['color']
        sb.tint_color       = 'white'
        sb.corner_radius    = 6
        sb.font             = ('<system>', 13)

        def make_h(name, sc=scroll):
            def h(s):
                geselecteerd[0] = name
                for sub in sc.subviews:
                    sub.background_color = '#555555'
                s.background_color = CLR_EVENT_SEL
            return h

        sb.action = make_h(info['name'])
        scroll.add_subview(sb)

    scroll.content_size = (w, rows * (btn_h + 4) + 8)
    return scroll

# ---------------------------------------------------------------------------
# Event popup
# ---------------------------------------------------------------------------
def show_popup(event_data, team):
    extra_type   = event_data.get('extra', 'none')
    team_name    = data['match']['home'] if team == 'home' else data['match']['away']
    players_list = data.get(team, [])
    clr_starter  = CLR_HOME_STARTER  if team == 'home' else CLR_AWAY_STARTER
    clr_sub = CLR_HOME_SUB if team == 'home' else CLR_AWAY_SUB

    pw  = min(500, int(_sw) - 20)
    PAD = 10
    popup                  = ui.View()
    popup.background_color = CLR_PANEL
    popup.corner_radius    = 14
    popup.frame            = (0, 0, pw, 700)

    selected_player    = [None]
    selected_extra     = [None]
    selected_sub_in = [None]
    own_goal         = [False]

    y = PAD

    # Titel
    titel            = ui.Label()
    titel.frame      = (PAD, y, pw - 2 * PAD, 34)
    titel.text       = (f'{get_icon(event_data["name"])} {event_data["name"]}'
                        f'  |  {team_name}  |  {state.event_time or format_time_log()}')
    titel.font       = ('<system-bold>', 16)
    titel.text_color = 'white'
    titel.alignment  = ui.ALIGN_CENTER
    popup.add_subview(titel)
    y += 44

    # ---- WISSEL ----
    if extra_type == 'sub':
        basis_namen  = state.starters(team)
        wissel_namen = state.subs(team)

        lbl_uit            = ui.Label()
        lbl_uit.frame      = (PAD, y, pw - 2 * PAD, 22)
        lbl_uit.text       = 'Speler UIT  (basisplayers):'
        lbl_uit.font       = ('<system-bold>', 13)
        lbl_uit.text_color = '#ff9999'
        popup.add_subview(lbl_uit)
        y += 26

        uit_info = [{'name': n, 'color': clr_starter} for n in basis_namen]
        make_player_scroll(popup, uit_info, PAD, y, pw - 2 * PAD, 140, selected_player)
        y += 150

        lbl_in            = ui.Label()
        lbl_in.frame      = (PAD, y, pw - 2 * PAD, 22)
        lbl_in.text       = 'Player IN  (substitutes):'
        lbl_in.font       = ('<system-bold>', 13)
        lbl_in.text_color = '#99ff99'
        popup.add_subview(lbl_in)
        y += 26

        in_info = [{'name': n, 'color': clr_sub} for n in wissel_namen]
        make_player_scroll(popup, in_info, PAD, y, pw - 2 * PAD, 140, selected_sub_in)
        y += 150

    else:
        # ---- EIGEN DOELPUNT ----
        if event_data['name'] in ('Goal', 'Penalty'):
            ed              = ui.Button(title='[ ] Own goal')
            ed.frame        = (PAD, y, pw - 2 * PAD, 34)
            ed.background_color = '#1e1e2e'
            ed.tint_color   = '#aaaaaa'
            ed.corner_radius = 6
            ed.font         = ('<system>', 14)
            def toggle_ed(s):
                own_goal[0] = not own_goal[0]
                s.title      = '[X] Own goal' if own_goal[0] else '[ ] Own goal'
                s.tint_color = '#e74c3c' if own_goal[0] else '#aaaaaa'
            ed.action = toggle_ed
            popup.add_subview(ed)
            y += 42

        # ---- SPELERSLIJST (uitgesloten players worden overgeslagen) ----
        sp_lbl            = ui.Label()
        sp_lbl.frame      = (PAD, y, pw - 2 * PAD, 22)
        sp_lbl.text       = 'Player:'
        sp_lbl.font       = ('<system-bold>', 13)
        sp_lbl.text_color = '#aaaaaa'
        popup.add_subview(sp_lbl)
        y += 26

        pl_info = []
        for player in players_list[:18]:
            if player['name'] in state.suspended:
                continue
            if state.status[team].get(player['name']) != 'starter':
                continue
            pl_info.append({'name': f'{player["number"]} {player["name"]}', 'color': clr_starter})

        scroll_h = min(max(-(-len(pl_info) // 2) * 42 + 8, 50), 200)
        make_player_scroll(popup, pl_info, PAD, y, pw - 2 * PAD, scroll_h, selected_player)
        y += scroll_h + 10

        # ---- ASSIST ----
        if extra_type == 'assist':
            as_lbl            = ui.Label()
            as_lbl.frame      = (PAD, y, pw - 2 * PAD, 22)
            as_lbl.text       = 'Assist:'
            as_lbl.font       = ('<system-bold>', 13)
            as_lbl.text_color = '#aaaaaa'
            popup.add_subview(as_lbl)
            y += 26

            # Only starters of same team, excluding the scorer
            raw    = selected_player[0] or ''
            scorer = raw.split(' ', 1)[1] if ' ' in raw and raw.split(' ', 1)[0].isdigit() else raw
            clr_a  = CLR_HOME_STARTER if team == 'home' else CLR_AWAY_STARTER
            assist_info = []
            for player in data.get(team, []):
                if player['name'] in state.suspended:
                    continue
                if player['name'] == scorer:
                    continue
                if state.status[team].get(player['name']) != 'starter':
                    continue
                assist_info.append({'name': player['name'], 'color': clr_a})

            as_h = min(max(-(-len(assist_info) // 2) * 42 + 8, 50), 160)
            make_player_scroll(popup, assist_info, PAD, y, pw - 2 * PAD, as_h, selected_extra)
            y += as_h + 10

        # ---- RESULTAAT ----
        elif extra_type == 'result':
            res_lbl            = ui.Label()
            res_lbl.frame      = (PAD, y, pw - 2 * PAD, 22)
            res_lbl.text       = 'Result:'
            res_lbl.font       = ('<system-bold>', 13)
            res_lbl.text_color = '#aaaaaa'
            popup.add_subview(res_lbl)
            y += 26
            seg          = ui.SegmentedControl()
            seg.frame    = (PAD, y, pw - 2 * PAD, 36)
            seg.segments = ['On target', 'Off target', 'Blocked']
            seg.name     = 'result_seg'
            popup.add_subview(seg)
            y += 46

        # ---- REDEN ----
        elif extra_type == 'reason':
            rl            = ui.Label()
            rl.frame      = (PAD, y, pw - 2 * PAD, 22)
            rl.text       = 'Reason:'
            rl.font       = ('<system-bold>', 13)
            rl.text_color = '#aaaaaa'
            popup.add_subview(rl)
            y += 26
            tf                  = ui.TextField()
            tf.name             = 'extra_field'
            tf.frame            = (PAD, y, pw - 2 * PAD, 38)
            tf.placeholder      = 'Description...'
            tf.background_color = '#1e1e2e'
            tf.text_color       = 'white'
            tf.corner_radius    = 6
            popup.add_subview(tf)
            y += 48

    # ---- NOTITIE ----
    nl            = ui.Label()
    nl.frame      = (PAD, y, pw - 2 * PAD, 22)
    nl.text       = 'Note (optional):'
    nl.font       = ('<system-bold>', 13)
    nl.text_color = '#aaaaaa'
    popup.add_subview(nl)
    y += 26
    note_tf                  = ui.TextField()
    note_tf.name             = 'note_field'
    note_tf.frame            = (PAD, y, pw - 2 * PAD, 38)
    note_tf.placeholder      = 'Extra info...'
    note_tf.background_color = '#1e1e2e'
    note_tf.text_color       = 'white'
    note_tf.corner_radius    = 6
    popup.add_subview(note_tf)
    y += 48

    popup.frame = (0, 0, pw, y + 54)

    # ---- KNOPPEN ----
    btn_w = (pw - 4 * PAD) // 3

    def confirm(s):
        player_raw = selected_player[0]
        if player_raw and ' ' in player_raw:
            parts  = player_raw.split(' ', 1)
            player = parts[1] if parts[0].isdigit() else player_raw
        else:
            player = player_raw

        extra_info = selected_extra[0] or ''
        tf  = popup['extra_field']
        seg = popup['result_seg']
        if tf and not extra_info:
            extra_info = tf.text or ''
        if seg and seg.selected_index >= 0 and not extra_info:
            extra_info = seg.segments[seg.selected_index]
        note = popup['note_field']
        if note and note.text:
            extra_info = (extra_info + ' | ' + note.text).strip(' |')

        if extra_type == 'sub':
            player_uit = player
            player_in  = selected_sub_in[0]
            if player_uit and player_in:
                state.status[team][player_uit] = 'sub'
                state.status[team][player_in]  = 'starter'
                extra_info = f'In: {player_in} | Uit: {player_uit}'
                player     = player_uit

        log_event(event_data, player, team, extra_info, own_goal[0])
        popup.close()

    def geen_player(s):
        extra_info = selected_extra[0] or ''
        tf  = popup['extra_field']
        seg = popup['result_seg']
        if tf and not extra_info:
            extra_info = tf.text or ''
        if seg and seg.selected_index >= 0 and not extra_info:
            extra_info = seg.segments[seg.selected_index]
        note = popup['note_field']
        if note and note.text:
            extra_info = (extra_info + ' | ' + note.text).strip(' |')
        log_event(event_data, None, team, extra_info, own_goal[0])
        popup.close()

    def cancel(s):
        popup.close()

    def make_action_btn(title, x, color, action):
        b                  = ui.Button(title=title)
        b.frame            = (x, y, btn_w, 44)
        b.background_color = color
        b.tint_color       = 'white'
        b.corner_radius    = 8
        b.font             = ('<system-bold>', 14)
        b.action           = action
        return b

    popup.add_subview(make_action_btn('Confirm',
        PAD, '#27ae60', confirm))
    popup.add_subview(make_action_btn('No player',
        PAD + btn_w + PAD, '#7f8c8d', geen_player))
    popup.add_subview(make_action_btn('Cancel',
        PAD + 2 * (btn_w + PAD), '#c0392b', cancel))

    popup.present('popover')

# ---------------------------------------------------------------------------
# Layout — auto scale based on screen size
# ---------------------------------------------------------------------------
import ui as _ui_screen
_sw, _sh = _ui_screen.get_screen_size()
COMPACT   = _sw < 500        # iPhone = compact, iPad = spacious

PAD        = 8  if COMPACT else 10
DISPLAY_H  = 56 if COMPACT else 72
SCORE_H    = 36 if COMPACT else 46
EVENT_H    = 42 if COMPACT else 54
EVENT_COLS = 4
EVENT_ROWS = 3
TEAM_BTN_H = 48 if COMPACT else 60
ACTION_H   = 40 if COMPACT else 50
LOG_H      = 100 if COMPACT else 150

# Font sizes
FS_DISPLAY   = 36 if COMPACT else 46
FS_SCORE     = 17 if COMPACT else 24
FS_EVENT     = 12 if COMPACT else 15
FS_TEAM      = 13 if COMPACT else 17
FS_ACTION    = 12 if COMPACT else 14
FS_LOG       = 11 if COMPACT else 13
FS_HINT      = 10 if COMPACT else 12

events_12  = (data.get('events', []) + [None] * 12)[:12]
total_w    = int(_sw) - 2 * PAD
ev_btn_w   = (total_w - (EVENT_COLS + 1) * PAD) // EVENT_COLS
team_btn_w = (total_w - 3 * PAD) // 2
sw_btn_w   = (total_w - 4 * PAD) // 3

total_h = (PAD + DISPLAY_H + PAD + SCORE_H + PAD +
           EVENT_ROWS * (EVENT_H + PAD) + PAD +
           22 + PAD +
           TEAM_BTN_H + PAD +
           ACTION_H + PAD +
           22 + LOG_H + PAD)

main_view                  = ui.View()
main_view.name             = f'{data["match"]["home"]} vs {data["match"]["away"]}'
main_view.background_color = CLR_BG
main_view.frame            = (0, 0, total_w, total_h)

y = PAD

# Clock display
display                  = ui.Label()
display.name             = 'display'
display.frame            = (PAD, y, total_w - 2 * PAD, DISPLAY_H)
display.text             = '00:00'
display.font             = ('<system-bold>', FS_DISPLAY)
display.text_color       = 'white'
display.alignment        = ui.ALIGN_CENTER
display.background_color = CLR_PANEL
display.corner_radius    = 10
main_view.add_subview(display)
y += DISPLAY_H + PAD

# Score
score_label                  = ui.Label()
score_label.name             = 'score_label'
score_label.frame            = (PAD, y, total_w - 2 * PAD, SCORE_H)
score_label.text             = f'{data["match"]["home"]}  0 - 0  {data["match"]["away"]}'
score_label.font             = ('<system-bold>', FS_SCORE)
score_label.text_color       = 'white'
score_label.alignment        = ui.ALIGN_CENTER
score_label.background_color = CLR_PANEL
score_label.corner_radius    = 8
main_view.add_subview(score_label)
y += SCORE_H + PAD

# Event buttons 4x3
for i, event in enumerate(events_12):
    if event is None:
        continue
    col = i % EVENT_COLS
    row = i // EVENT_COLS
    x   = PAD + col * (ev_btn_w + PAD)
    ey  = y + row * (EVENT_H + PAD)
    btn                  = ui.Button(title=f'{get_icon(event["name"])} {event["name"]}')
    btn.name             = event['name']
    btn.frame            = (x, ey, ev_btn_w, EVENT_H)
    btn.background_color = CLR_EVENT_IDLE
    btn.tint_color       = 'white'
    btn.corner_radius    = 10
    btn.font             = ('<system-bold>', FS_EVENT)
    btn.enabled          = False
    btn.action           = tapped_event
    main_view.add_subview(btn)

y += EVENT_ROWS * (EVENT_H + PAD) + PAD

# Hint label
hint            = ui.Label()
hint.name       = 'hint_label'
hint.frame      = (PAD, y, total_w - 2 * PAD, 20)
hint.text       = 'Select an event first, then Home or Away'
hint.font       = ('<system>', FS_HINT)
hint.text_color = '#555555'
hint.alignment  = ui.ALIGN_CENTER
main_view.add_subview(hint)
y += 22 + PAD

# Home / Away buttons
home_btn                  = ui.Button(title=f'Home: {data["match"]["home"]}')
home_btn.name             = 'home_btn'
home_btn.frame            = (PAD, y, team_btn_w, TEAM_BTN_H)
home_btn.background_color = CLR_HOME_STARTER
home_btn.tint_color       = 'white'
home_btn.corner_radius    = 10
home_btn.font             = ('<system-bold>', FS_TEAM)
home_btn.action           = tapped_team
main_view.add_subview(home_btn)

away_btn                  = ui.Button(title=f'Away: {data["match"]["away"]}')
away_btn.name             = 'away_btn'
away_btn.frame            = (PAD + team_btn_w + PAD, y, team_btn_w, TEAM_BTN_H)
away_btn.background_color = CLR_AWAY_STARTER
away_btn.tint_color       = 'white'
away_btn.corner_radius    = 10
away_btn.font             = ('<system-bold>', FS_TEAM)
away_btn.action           = tapped_team
main_view.add_subview(away_btn)
y += TEAM_BTN_H + PAD

# Clock display knoppen rij: [Opstelling] [Start/Pause/Resume] [Einde Periode x]
def make_btn(name, title, x, by, w, h, color, action, enabled=True):
    btn                  = ui.Button(title=title)
    btn.name             = name
    btn.frame            = (x, by, w, h)
    btn.background_color = color
    btn.tint_color       = 'white'
    btn.corner_radius    = 8
    btn.font             = ('<system-bold>', FS_ACTION)
    btn.action           = action
    btn.enabled          = enabled
    return btn

third_w = (total_w - 4 * PAD) // 3

main_view.add_subview(make_btn('lineup_btn', 'Set lineup',
    PAD, y, third_w, ACTION_H, '#8e44ad',
    lambda s: show_lineup_screen()))

main_view.add_subview(make_btn('start_pause_btn', 'Start',
    2 * PAD + third_w, y, third_w, ACTION_H, '#27ae60',
    tapped_start, enabled=False))

main_view.add_subview(make_btn('end_btn', 'End Period 1',
    3 * PAD + 2 * third_w, y, third_w, ACTION_H, '#555555',
    tapped_end, enabled=False))

y += ACTION_H + PAD

# Match log
log_lbl            = ui.Label()
log_lbl.frame      = (PAD, y, total_w - 2 * PAD, 22)
log_lbl.text       = 'Match log'
log_lbl.font       = ('<system-bold>', 13)
log_lbl.text_color = '#aaaaaa'
main_view.add_subview(log_lbl)
y += 24

log_tv                  = ui.TextView()
log_tv.name             = 'log_view'
log_tv.frame            = (PAD, y, total_w - 2 * PAD, LOG_H)
log_tv.background_color = CLR_PANEL
log_tv.text_color       = '#00ff99'
log_tv.font             = ('<system>', FS_LOG)
log_tv.corner_radius    = 8
log_tv.editable         = False
main_view.add_subview(log_tv)
y += LOG_H + PAD

# (Save Match button removed - saving via End Match popup)

# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------
main_view.present('sheet')
