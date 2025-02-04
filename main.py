import time
import json
import base64
import random
import requests
import pandas as pd
from datetime import datetime, timedelta
from googletrans import Translator

import streamlit as st
import streamlit_antd_components as sac
from streamlit_extras.stylable_container import stylable_container

import firebase_admin
from firebase_admin import auth, credentials

from backend.endpoints import MLBStatsAPI, CloudTranslationAPI
from backend.completions import VertexAIFreeform, VertexAIVision, VertexAIChat
from backend.utils import MLBPlayUtils

from database.cloud_sql import UsersTable
from database.cloud_storage import MLBStorageBucket
from database.firestore import MLBLiveFeedSummaryCollection


st.set_page_config(
    page_title="PlayBook Live",
    page_icon=":material/sports_baseball:",
    initial_sidebar_state="expanded",
    layout="wide",
)



st.markdown(
    """
    <style>
           .block-container {
                padding-top: 2rem;
                padding-bottom: 1.55rem;
            }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
        h1, h2, h3, h4, h5, h6 {
            position: relative;
        }
        .stMarkdown a {
            display: none !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)



with open("assets/css/play_by_play.css") as f:
    css = f.read()

st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)



if "username" not in st.session_state:
    st.session_state.username = None

if "selected_language" not in st.session_state:
    st.session_state.selected_language = "English"

if "selected_match" not in st.session_state:
    st.session_state.selected_match = None

if "matches_on_game_date" not in st.session_state:
    st.session_state.matches_on_game_date = {}

if "result_count" not in st.session_state:
    st.session_state.result_count = -3

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "game_status" not in st.session_state:
    st.session_state.game_status = 'live'

if "cache_play_banners" not in st.session_state:
    st.session_state.cache_play_banners = {}

if "selected_date" not in st.session_state:
    st.session_state.selected_date = "today"

if "display_play_data_interface" not in st.session_state:
    st.session_state.display_play_data_interface = False

if "global_language_codes" not in st.session_state:
    st.session_state.global_language_codes = {
        "English": "en",
        "Spanish": "es",
        "Japanese": "ja",
        "Hindi": "hi"
    }



def set_display_play_data_interface_to_true():
    st.session_state.display_play_data_interface = True

def set_display_play_data_interface_to_false():
    st.session_state.display_play_data_interface = False


def t(text, target_language=st.session_state.selected_language):
    if target_language == 'English':
        return text

    translator = Translator()

    target_language = st.session_state.global_language_codes.get(target_language)

    try:
        translation = translator.translate(text, dest=target_language)
        return translation.text

    except Exception as e:
        return text


@st.dialog(t('Key Moments from the Game'), width='large')
def popup_display_key_moments(title, video_url):
    st.markdown(f"<H2>{title}</H2>", unsafe_allow_html=True)
    st.video(video_url)


@st.dialog(t('Account Preferences'), width='large')
def account_preferences():
    supported_languages = ['English', 'Hindi', 'Spanish', 'Japanese']

    cola, colb = st.columns([2.5, 1], vertical_alignment='bottom')

    with cola:
        language_choice = st.selectbox(
            t("Choose Language"), 
            supported_languages, 
            index=supported_languages.index(st.session_state.selected_language)
        )

    with colb:
        pref_button = st.button(t("Update Preferences"))
            
    if pref_button:
        st.session_state.selected_language = language_choice
        st.success("Updated your preferences", icon=":material/check:")

        time.sleep(3)
        st.rerun()


@st.dialog(t('Create New Account'), width='large')
def create_account():
    with st.form("_form_create_account", border=False, clear_on_submit=False):
        signup_form_section_1, signup_form_section_2 = st.columns(2)

        with signup_form_section_1:
            name = st.text_input(
                "Enter your Full Name:",
            )
            email = st.text_input(
                "Enter your E-Mail Id:",
            )

        with signup_form_section_2:
            username = st.text_input(
                "Enter your Username:",
                placeholder="Allowed characters: A-Z, 0-9, . & _",
            )
            phone_number = st.text_input(
                "Enter Phone Number:",
                placeholder="Include your Country Code (eg: +91)",
            )

        cola, colb = st.columns(2)

        with cola:
            password = st.text_input(
                "Enter your Password:",
                type="password",
            )

        mlb_stats_api = MLBStatsAPI()
        available_teams = mlb_stats_api.get_all_teams(only_mlb=True)

        with colb:
            favourite_team = st.selectbox(
                "Select your Favourite Team:", 
                list(available_teams.keys()), 
                index=None, 
                placeholder="Select your Favourite Team:", 
            )
        
        teams_to_follow = st.multiselect(
            "Select Teams to Follow:", 
            list(available_teams.keys()), 
            placeholder="Select Teams to Follow:", 
        )

        accept_terms_and_conditions = st.checkbox(
            "By creating an account, you confirm your acceptance to our Terms of Use and the Privacy Policy"
        )

        button_section_1, button_section_2, button_section_3 = st.columns(3)

        with button_section_1:
            button_submit_create_account = st.form_submit_button(
                "Create New Account", use_container_width=True
            )
        
        if button_submit_create_account:
            try:
                if not name:
                    st.warning("Please enter your full name")

                elif not email:
                    st.warning("Please enter your email id")

                elif not username:
                    st.warning("Please enter your username")

                elif not phone_number:
                    st.warning("Please enter your phone number")
                
                elif not password:
                    st.warning("Please enter your password")
                
                elif not accept_terms_and_conditions:
                    st.warning("Please accept our terms of use")

                else:
                    ids_teams_to_follow = [available_teams[team] for team in teams_to_follow]
                    id_favourite_team = available_teams[favourite_team]

                    firebase_admin.auth.create_user(
                        uid=username.lower(),
                        display_name=name,
                        email=email,
                        phone_number=phone_number,
                        password=password,
                    )

                    try:
                        users_sql_table = UsersTable()

                        users_sql_table.add_user(
                            username.lower(), 
                            id_favourite_team, 
                            ids_teams_to_follow, []
                        )
                    
                    except: pass

                    alert_successful_account_creation = st.success(
                        "Your Account has been created successfully",
                        icon=":material/how_to_reg:",
                    )

                    time.sleep(3)
                    alert_successful_account_creation.empty()
                    st.rerun()

            except Exception as error:
                st.warning(error)


@st.dialog("What Happened Here? Ask Gemini.", width="large")
def ask_gemini(play, play_summary):
    query = st.text_area(
        "Got Questions About This Play? Ask Gemini.",
        placeholder="Got Questions About This Play? Ask Gemini.",
        label_visibility='collapsed',
    )

    if st.button("Ask Gemini", icon=":material/robot_2:"):
        vertex_ai_chat = VertexAIChat()

        response = vertex_ai_chat.ask_gemini_questions_about_play(query, play, play_summary)
        st.info(response)


@st.dialog(t("Game Play Details"), width="large")
def display_play_details(play_id, play, play_banner):
    cola, colb = st.columns([1, 4.5])

    cola.image(play_banner)

    with colb:
        st.markdown(
            f"""
            <div class="div-truncate-heading">
                <H3 class="h3-base">
                    {t(play.get("result").get("description"))}
                </H3>
            </div>

            <P class="p-play-analysis-dialog-outcome">
                <B>{t("Batter")}:</B> {t(play.get('matchup').get('batter').get('fullName'))} &nbsp;•&nbsp; 
                <B>{t("Pitcher")}:</B> {t(play.get('matchup').get('pitcher').get('fullName'))}
            </P>

            <div class="div-truncate-text">
                <P>
                    {st.session_state.play_summaries.get(play_id).get('outcome')}
                </P>
            </div>
            """, 
            unsafe_allow_html=True,
        )

    tab_dialog = sac.tabs([
        sac.TabsItem(label=t('Play Breakdown')),
        sac.TabsItem(label=t('Game Strategy')),
        sac.TabsItem(label=t('Snapshot')),
    ], variant='outline')

    if tab_dialog == t("Play Breakdown"):
        st.markdown(
            f"""
            <P>
                {st.session_state.play_summaries.get(play_id).get('setup')}
            </P>

            <P>
                {st.session_state.play_summaries.get(play_id).get('summary_of_play_events')}
            </P>
            """, 
            unsafe_allow_html=True
        )

    if tab_dialog == t("Game Strategy"):
        st.markdown(
            f"""
            <P>
                {st.session_state.play_summaries.get(play_id).get('overall_strategy_insights')}
            </P>
            """, 
            unsafe_allow_html=True
        )

    if tab_dialog == t("Snapshot"):
        cola, colb = st.columns([1, 2])

        with cola:
            st.markdown(
                f"""
                <P>
                <B>{t("Basic Game Info")}</B>
                <ul>
                    <li>{t("Play Type")}: {t(play.get("result").get("event", "Unknown"))}
                    <li>{t("Inning")}: {"Top" if play.get("about").get("isTopInning", False) else "Bottom"} {play.get("about").get("inning", "N/A")}
                    <li>{t("Runs Scored")}: {play.get("result").get("rbi", 0)} ({t("Outs")}: {play.get('count').get('outs',0)})
                    <li>{t("Count")}: {play.get("count").get('balls', 0)} {t("Balls")} - {play.get("count").get('strikes', 0)} {t("Strikes")}
                    <li>{t("Score")}: {t("Away")} {play.get("result").get("awayScore", "N/A")} - {t("Home")} {play.get("result").get("homeScore", "N/A")}
                </ul>
                </P>
                """, 
                unsafe_allow_html=True,
            )

        with colb:
            st.markdown(
                f"""
                <P>
                    <B>{t("Player Info")}</B>
                    <ul>
                        <li>{t("Batter")}: {t(play.get('matchup').get('batter').get('fullName'))} ({t("Bat Side")}: {t(play.get('matchup').get('batSide').get('description'))})</li>
                        <li>{t("Pitcher")}: {t(play.get('matchup').get('pitcher').get('fullName'))} ({t("Pitch Hand")}: {t(play.get('matchup').get('pitchHand').get('description'))})</li>
                    </ul>
                </P>
                """, 
                unsafe_allow_html=True
            )

            colx, coly =st.columns(2)
            play_events_data = play.get('playEvents')

            if play_events_data and any(event.get('isPitch') for event in play_events_data):
                pitch_event = next(event for event in play_events_data if event.get('isPitch'))
                pitch_data = pitch_event.get('pitchData')

                if pitch_data:
                    with colx:
                        st.markdown(
                            f"""
                            <li>{t("Pitch Speed")}: {t(pitch_data.get('startSpeed'))}</li>
                            <li>{t("Pitch Type")}: {t(pitch_event.get('details', {}).get('type', {}).get('description'))}</li>
                            """, 
                            unsafe_allow_html=True
                        )

            hit_data = pitch_event.get('hitData') if pitch_event else None

            if hit_data:
                with coly:
                    st.markdown(
                        f"""
                        <ul>
                            <li>{t("Launch Speed:")} {t(hit_data.get('launchSpeed'))}</li>
                            <li>{t("Launch Angle")}: {t(hit_data.get('launchAngle'))}</li>
                            <li>{t("Hit Distance")}: {t(hit_data.get('totalDistance'))}</li>
                        </ul>
                        """, 
                        unsafe_allow_html=True
                    )



if __name__ == '__main__':
    if st.session_state.username:
        with st.sidebar:
            selected_menu_item = sac.menu(
                [
                    sac.MenuItem(
                        t("PlayBook Live Dashboard"),
                        icon="grid",
                    ),
                    sac.MenuItem(" ", disabled=True),
                    sac.MenuItem(type="divider"),
                ],
                open_all=True,
            )

        if selected_menu_item == t("PlayBook Live Dashboard"):
            with st.sidebar:
                if not st.session_state.display_play_data_interface:
                    with st.container(height=350, border=False):
                        st.session_state.selected_date = st.date_input(
                            "Select Game Day", 
                            value=st.session_state.selected_date,
                            max_value=datetime.now().date(), 
                            format="DD-MM-YYYY", 
                            label_visibility='collapsed', 
                            help="By default, toady's date is selected",
                        )

                        mlb_stats_api = MLBStatsAPI()
                        st.session_state.matches_on_game_date = mlb_stats_api.get_mlb_schedule(st.session_state.selected_date)

                        placeholder_text = t("Select match to explore") if len(st.session_state.matches_on_game_date.keys()) > 0 else t("No games available for selected date")

                        st.session_state.selected_match = st.selectbox(
                            "Select the Match", 
                            st.session_state.matches_on_game_date.keys(), 
                            index=None, 
                            placeholder=placeholder_text,
                            label_visibility='collapsed'
                        )

                        button_explore_games = st.button(
                            t("Explore Game Feed"), 
                            icon=":material/rocket_launch:",
                            on_click=set_display_play_data_interface_to_true, 
                            use_container_width=True, 
                            disabled=False if len(st.session_state.matches_on_game_date.keys()) > 0 else True,
                        )
                    
                    cola, colb = st.columns([4.5, 1])
                    
                    with cola:
                        if st.button(t("Account Preferences"), icon=':material/tune:', use_container_width=True):
                            account_preferences()

                    with colb:
                        if st.button("", icon=':material/logout:', use_container_width=True):
                            st.session_state.clear()
                            st.rerun()


            if st.session_state.display_play_data_interface:
                with st.sidebar:
                    with st.container(height=350, border=False):
                        pass

                    cola, colb = st.columns([4.5, 1])

                    with cola:
                        if st.button(t("Back to Game Selection"), icon=':material/tune:', use_container_width=True):
                            temp_username = st.session_state.username

                            temp_user_display_name = st.session_state.user_display_name
                            temp_selected_date = st.session_state.selected_date

                            st.session_state.clear()

                            if "username"not in st.session_state:
                                st.session_state.username = temp_username

                            if "user_display_name"not in st.session_state:
                                st.session_state.user_display_name = temp_user_display_name
                            
                            if "selected_date" not in st.session_state:
                                st.session_state.selected_date = temp_selected_date

                            st.rerun()

                    with colb:
                        if st.button("", icon=':material/logout:', use_container_width=True):
                            st.session_state.clear()
                            st.rerun()

                if "game_pk" not in st.session_state:
                    st.session_state.game_pk = st.session_state.matches_on_game_date.get(st.session_state.selected_match)

                if ("live_feed_api_response" not in st.session_state) or (st.session_state.game_status.lower() == 'live'):
                    mlb_stats_api = MLBStatsAPI()
                    st.session_state.live_feed_api_response = mlb_stats_api.get_mlb_live_feed(st.session_state.game_pk)

                    st.session_state.game_status = st.session_state.live_feed_api_response.get("gameData", {}).get("status", {}).get("abstractGameState")

                all_plays = st.session_state.live_feed_api_response.get("liveData", {}).get("plays", {}).get("allPlays", [])

                with st.container(border=False):
                    cola, colb, colc, cold, cole = st.columns(
                        [4, 0.75, 1.5, 0.75, 4], 
                        vertical_alignment='center'
                    )

                    with colb:
                        away_team_id = st.session_state.live_feed_api_response.get("gameData").get("teams").get("away").get("id")
                        st.image(
                            f'https://www.mlbstatic.com/team-logos/{away_team_id}.svg',
                            use_container_width=True,
                        )
                    with cola:
                        away_team_name = t(st.session_state.live_feed_api_response.get("gameData").get("teams").get("away").get("name"))
                        
                        team_type = t("Away Team")
                        st.markdown(
                            f"""
                            <H4 class='h4-base' align='right'>
                                {away_team_name}&nbsp;&nbsp;
                            </H4>

                            <P align='right'>
                                {team_type} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                            </P>
                            """, 
                            unsafe_allow_html=True
                        )
                            
                    with colc:
                        st.markdown(
                            f"""
                            <H4 align='center'>
                                {all_plays[-1].get('result').get('awayScore')}&nbsp;&nbsp; - &nbsp;&nbsp;{all_plays[-1].get('result').get('homeScore')}
                            </H4>
                            """, 
                            unsafe_allow_html=True
                        )

                    with cold:
                        home_team_id = st.session_state.live_feed_api_response.get("gameData").get("teams").get("home").get("id")
                        st.image(
                            f'https://www.mlbstatic.com/team-logos/{home_team_id}.svg',
                            use_container_width=True,
                        )
                    with cole:
                        home_team_name = t(st.session_state.live_feed_api_response.get("gameData").get("teams").get("home").get("name"))
                        
                        team_type = t("Home Team")
                        st.markdown(
                            f"""
                            <H4 class='h4-base' align='left'>
                                &nbsp;&nbsp;&nbsp;{home_team_name}
                            </H4>

                            <P align='left'>
                                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{team_type}
                            </P>
                            """, 
                            unsafe_allow_html=True
                        )

                    st.write(" ")
                    venue = t("Venue")
                    st.markdown(
                        f"""
                        <center>
                            {venue}: 
                            {t(st.session_state.live_feed_api_response.get('gameData').get('venue').get('name'))}, 
                            {t(st.session_state.live_feed_api_response.get('gameData').get('venue').get('location').get('city'))}, 
                            {st.session_state.live_feed_api_response.get('gameData').get('venue').get('location').get('stateAbbrev')}
                        </center>
                        """, 
                        unsafe_allow_html=True
                    )

                    st.markdown("<BR>", unsafe_allow_html=True)
                    mlb_play_utils = MLBPlayUtils()

                    st.dataframe(
                        mlb_play_utils.create_scorecard(st.session_state.live_feed_api_response),
                        use_container_width=True
                    )

                with st.container(border=False):
                    tab_dashboard = sac.tabs([
                        sac.TabsItem(label=t('Play-by-Play Analysis')),
                        sac.TabsItem(label=t('Team Lineups')),
                        sac.TabsItem(label=t('Key Moments')),
                    ])

                    if tab_dashboard == t('Play-by-Play Analysis'):
                        if ("play_summaries" not in st.session_state) or (st.session_state.game_status.lower() == 'live'):
                            mlb_live_feed_collection = MLBLiveFeedSummaryCollection()

                            st.session_state.play_summaries = mlb_live_feed_collection.fetch_live_feed_summary(
                                st.session_state.game_pk,
                                st.session_state.selected_language
                            )

                        play_ids_with_summary = st.session_state.play_summaries.keys() if st.session_state.play_summaries else {}

                        vertext_ai_freeform = VertexAIFreeform()
                        vertex_ai_vision = VertexAIVision()
                        mlb_storage_bucket = MLBStorageBucket()
                        mlb_live_feed_collection = MLBLiveFeedSummaryCollection()
                        cloud_translation_api = CloudTranslationAPI()

                        result_count_ribbon = f"Showing results for last {(st.session_state.result_count+1)*-1} plays of the game"

                        st.markdown(
                            f"<P align='left'>{t(result_count_ribbon)}</P>", 
                            unsafe_allow_html=True
                        )

                        for play in all_plays[-1:st.session_state.result_count:-1]:
                            play_banner = None
                            play_id = play.get('playEvents', [])[-1].get('playId')

                            with st.spinner("Fetching game data.... this might take a minute"):
                                if play_id not in play_ids_with_summary:
                                    play_summary = vertext_ai_freeform.generate_play_by_play_summary(play)
                                    play_summary_json = json.loads(play_summary)

                                    image_prompt = play_summary_json.get("image_prompt")

                                    outcome_es = cloud_translation_api.translate_text(play_summary_json.get('outcome'), 'Spanish')
                                    overall_strategy_insights_es = cloud_translation_api.translate_text(play_summary_json.get('overall_strategy_insights'), 'Spanish')
                                    setup_es = cloud_translation_api.translate_text(play_summary_json.get('setup'), 'Spanish')
                                    summary_of_play_events_es = cloud_translation_api.translate_text(play_summary_json.get('summary_of_play_events'), 'Spanish')
                                    title_es = cloud_translation_api.translate_text(play_summary_json.get('title'), 'Spanish')

                                    play_summary_es_json = {
                                        'image_prompt': image_prompt,
                                        'outcome': outcome_es,
                                        'overall_strategy_insights': overall_strategy_insights_es,
                                        'setup': setup_es,
                                        'summary_of_play_events': summary_of_play_events_es,
                                        'title': title_es,
                                    }

                                    outcome_ja = cloud_translation_api.translate_text(play_summary_json.get('outcome'), 'Japanese')
                                    overall_strategy_insights_ja = cloud_translation_api.translate_text(play_summary_json.get('overall_strategy_insights'), 'Japanese')
                                    setup_ja = cloud_translation_api.translate_text(play_summary_json.get('setup'), 'Japanese')
                                    summary_of_play_events_ja = cloud_translation_api.translate_text(play_summary_json.get('summary_of_play_events'), 'Japanese')
                                    title_ja = cloud_translation_api.translate_text(play_summary_json.get('title'), 'Japanese')

                                    play_summary_ja_json = {
                                        'image_prompt': image_prompt,
                                        'outcome': outcome_ja,
                                        'overall_strategy_insights': overall_strategy_insights_ja,
                                        'setup': setup_ja,
                                        'summary_of_play_events': summary_of_play_events_ja,
                                        'title': title_ja,
                                    }

                                    outcome_hi = cloud_translation_api.translate_text(play_summary_json.get('outcome'), 'Hindi')
                                    overall_strategy_insights_hi = cloud_translation_api.translate_text(play_summary_json.get('overall_strategy_insights'), 'Hindi')
                                    setup_hi = cloud_translation_api.translate_text(play_summary_json.get('setup'), 'Hindi')
                                    summary_of_play_events_hi = cloud_translation_api.translate_text(play_summary_json.get('summary_of_play_events'), 'Hindi')
                                    title_hi = cloud_translation_api.translate_text(play_summary_json.get('title'), 'Hindi')

                                    play_summary_hi_json = {
                                        'image_prompt': image_prompt,
                                        'outcome': outcome_hi,
                                        'overall_strategy_insights': overall_strategy_insights_hi,
                                        'setup': setup_hi,
                                        'summary_of_play_events': summary_of_play_events_hi,
                                        'title': title_hi,
                                    }

                                    if st.session_state.selected_language.lower() == 'english':
                                        st.session_state.play_summaries[play_id] = play_summary_json

                                    elif st.session_state.selected_language.lower() == 'spanish':
                                        st.session_state.play_summaries[play_id] = play_summary_es_json

                                    elif st.session_state.selected_language.lower() == 'japanese':
                                        st.session_state.play_summaries[play_id] = play_summary_ja_json

                                    elif st.session_state.selected_language.lower() == 'hindi':
                                        st.session_state.play_summaries[play_id] = play_summary_hi_json

                                    play_image_prompt = st.session_state.play_summaries.get(play_id).get('image_prompt')

                                    try:
                                        play_banner = vertex_ai_vision.generate_play_banner(play_image_prompt)

                                    except Exception as error:
                                        play_banner = "assets/placeholders/play_placeholder.png"

                                    if play_banner != "assets/placeholders/play_placeholder.png":
                                        mlb_storage_bucket.upload_play_banner(
                                            st.session_state.game_pk, 
                                            play_id, 
                                            play_banner
                                        )

                                    st.session_state.cache_play_banners[play_id] = play_banner

                                    try:
                                        mlb_live_feed_collection.add_play_summary(
                                            game_pk=st.session_state.game_pk, 
                                            data_english={play_id: play_summary_json},
                                            data_spanish={play_id: play_summary_es_json},
                                            data_japanese={play_id: play_summary_ja_json},
                                            data_hindi={play_id: play_summary_hi_json},
                                        )

                                    except Exception as error: pass

                                else:
                                    if play_id in st.session_state.cache_play_banners:
                                        play_banner = st.session_state.cache_play_banners[play_id]

                                    else:
                                        play_banner = mlb_storage_bucket.fetch_play_banner(st.session_state.game_pk, play_id)

                                        if not play_banner:
                                            play_image_prompt = st.session_state.play_summaries.get(play_id).get('image_prompt')

                                            try:
                                                vertex_ai_vision = VertexAIVision()
                                                play_banner = vertex_ai_vision.generate_play_banner("Generate the image of a baseball play")
                                                
                                                mlb_storage_bucket.upload_play_banner(
                                                    st.session_state.game_pk, 
                                                    play_id, 
                                                    play_banner
                                                )

                                            except Exception as error:
                                                play_banner = "assets/placeholders/play_placeholder.png"
                                        
                                        st.session_state.cache_play_banners[play_id] = play_banner

                            play_title = st.session_state.play_summaries.get(play_id).get('title')
                            play_event_summary = st.session_state.play_summaries.get(play_id).get('summary_of_play_events')

                            play_home_score = play.get('result').get('homeScore')
                            play_away_score = play.get('result').get('awayScore')
                            play_batter = t(play.get('matchup').get('batter').get('fullName'))
                            play_pitcher = t(play.get('matchup').get('pitcher').get('fullName'))

                            with stylable_container(
                                key="container_with_border",
                                css_styles="""
                                    {
                                        background-color: #181818;
                                        border: 1px solid rgba(49, 51, 63, 0.2);
                                        border-radius: 0.6rem;
                                        padding: calc(1em - 1px)
                                    }
                                    """,
                            ):
                                cola, colb, colc = st.columns([0.85, 2.71, 1.5])

                                with cola:
                                    try:
                                        st.image(
                                            play_banner, use_container_width=True,
                                        )
                                    except: pass

                                with colb:
                                    st.markdown(
                                        f"<H5>{play_title}</H5>", 
                                        unsafe_allow_html=True
                                    )
                                    
                                    colx, coly = st.columns([20, 0.01])

                                    with colx:
                                        st.markdown(
                                            f"""
                                            <P class="p-service-request-request-id-serial-number">
                                                {t("Batter")}: {play_batter} &nbsp;•&nbsp; {t("Pitcher")}: {play_pitcher}
                                            </P>
                                            """,
                                            unsafe_allow_html=True
                                        )

                                        st.markdown(
                                            f"""
                                            <div class="div-truncate-text">
                                                <P align='left'>
                                                    {play_event_summary}...
                                                </P>
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                with colc:
                                    st.markdown("<BR>", unsafe_allow_html=True)

                                    st.markdown(
                                        f"""
                                        <P class="p-service-request-status" align='right'>
                                            <font size=4>
                                                <B>
                                                    {t("Away")}: {play_away_score} &nbsp;•&nbsp; {t("Home")}: {play_home_score} &nbsp;
                                                </B>
                                            </font>
                                        </P>
                                        """, 
                                        unsafe_allow_html=True,
                                    )

                                    st.write(" ")
                                    colx, coly = st.columns([0.9, 3])

                                    with colx:
                                        if st.button(
                                            "", 
                                            icon=":material/chat:", 
                                            use_container_width=True, 
                                            key=f"_ask_gemini_{play_id}"
                                        ):
                                            ask_gemini(
                                                play, 
                                                st.session_state.play_summaries.get(play_id),
                                            )

                                    with coly:
                                        if st.button(
                                            t("View Details"), 
                                            icon=":material/page_info:", 
                                            use_container_width=True, 
                                            key=f"_view_details_{play_id}"
                                        ):
                                            display_play_details(play_id, play, play_banner)

                        if st.button(
                            t("Load Previous Plays"), 
                            icon=":material/read_more:", 
                            type='tertiary',
                        ):
                            st.session_state.result_count = max(
                                len(all_plays)*-1, 
                                st.session_state.result_count-2
                            )

                            st.rerun()

                    if tab_dashboard == t("Team Lineups"):
                        _, col = st.columns([3, 1])
                        selected_team = col.selectbox(
                            t("Select Team"), 
                            ['Away Team', 'Home Team'], 
                            label_visibility='collapsed'
                        )
                        st.write(" ")

                        mlb_play_utils = MLBPlayUtils()
                        all_players = mlb_play_utils.get_player_details(st.session_state.live_feed_api_response)

                        cola, colb, colc, cold, cole = st.columns(5)

                        for idx, player_id in enumerate(all_players[selected_team.replace(" Team", "").lower()]):
                            if idx % 5 == 0:
                                with cola:
                                    player_image_url = f"https://securea.mlb.com/mlb/images/players/head_shot/{all_players[selected_team.replace(' Team', '').lower()][player_id]['player_id']}.jpg"
                                    st.image(player_image_url, use_container_width=True)
                                    
                                    st.markdown(f"""
                                        <H6>{t(all_players[selected_team.replace(' Team', '').lower()][player_id]['full_name'])}</H6><BR>
                                        """, 
                                        unsafe_allow_html=True
                                    )
                            
                            elif idx % 5 == 1:
                                with colb:
                                    player_image_url = f"https://securea.mlb.com/mlb/images/players/head_shot/{all_players[selected_team.replace(' Team', '').lower()][player_id]['player_id']}.jpg"
                                    st.image(player_image_url, use_container_width=True)
                                    
                                    st.markdown(f"""
                                        <H6>{t(all_players[selected_team.replace(' Team', '').lower()][player_id]['full_name'])}</H6><BR>
                                        """, 
                                        unsafe_allow_html=True
                                    )

                            elif idx % 5 == 2:
                                with colc:
                                    player_image_url = f"https://securea.mlb.com/mlb/images/players/head_shot/{all_players[selected_team.replace(' Team', '').lower()][player_id]['player_id']}.jpg"
                                    st.image(player_image_url, use_container_width=True)
                                    
                                    st.markdown(f"""
                                        <H6>{t(all_players[selected_team.replace(' Team', '').lower()][player_id]['full_name'])}</H6><BR>
                                        """, 
                                        unsafe_allow_html=True
                                    )

                            elif idx % 5 == 3:
                                with cold:
                                    player_image_url = f"https://securea.mlb.com/mlb/images/players/head_shot/{all_players[selected_team.replace(' Team', '').lower()][player_id]['player_id']}.jpg"
                                    st.image(player_image_url, use_container_width=True)
                                    
                                    st.markdown(f"""
                                        <H6>{t(all_players[selected_team.replace(' Team', '').lower()][player_id]['full_name'])}</H6><BR>
                                        """, 
                                        unsafe_allow_html=True
                                    )
                            
                            elif idx % 5 == 4:
                                with cole:
                                    player_image_url = f"https://securea.mlb.com/mlb/images/players/head_shot/{all_players[selected_team.replace(' Team', '').lower()][player_id]['player_id']}.jpg"
                                    st.image(player_image_url, use_container_width=True)
                                    
                                    st.markdown(f"""
                                        <H6>{t(all_players[selected_team.replace(' Team', '').lower()][player_id]['full_name'])}</H6><BR>
                                        """, 
                                        unsafe_allow_html=True
                                    )

                    if tab_dashboard == t("Key Moments"):
                        if "game_highlight_videos" not in st.session_state:
                            mlb_stats_api = MLBStatsAPI()
                            st.session_state.game_highlight_videos = mlb_stats_api.get_game_highlight_videos(st.session_state.game_pk)
                        
                        if st.session_state.game_highlight_videos:
                            cola, colb, colc = st.columns(3)

                            for idx, highlight in enumerate(st.session_state.game_highlight_videos):
                                if idx % 3 == 0:
                                    with cola:
                                        st.video(st.session_state.game_highlight_videos[highlight])
                                        st.markdown(f"<H6>{t(highlight)}</H6>", unsafe_allow_html=True)

                                        if st.button("Expand Video", key=f'_highligh_{idx}', use_container_width=True):
                                            popup_display_key_moments(
                                                highlight, 
                                                st.session_state.game_highlight_videos[highlight]
                                            )
                                        
                                        st.write(" ")
                                
                                elif idx % 3 == 1:
                                    with colb:
                                        st.video(st.session_state.game_highlight_videos[highlight])
                                        st.markdown(f"<H6>{t(highlight)}</H6>", unsafe_allow_html=True)

                                        if st.button("Expand Video", key=f'_highligh_{idx}', use_container_width=True):
                                            popup_display_key_moments(
                                                highlight, 
                                                st.session_state.game_highlight_videos[highlight]
                                            )

                                        st.write(" ")

                                if idx % 3 == 2:
                                    with colc:
                                        st.video(st.session_state.game_highlight_videos[highlight])
                                        st.markdown(f"<H6>{t(highlight)}</H6>", unsafe_allow_html=True)

                                        if st.button("Expand Video", key=f'_highligh_{idx}', use_container_width=True):
                                            popup_display_key_moments(
                                                highlight, 
                                                st.session_state.game_highlight_videos[highlight]
                                            )

                                        st.write(" ")

            else:
                st.markdown(
                    f"""<BR><BR><BR><BR><BR><BR><BR>
                    <center>
                        <H5 class="h5-base">{t("Select a Baseball Game")}</H5>
                        {t("Choose a game to get Live Analysis, Highlights and more")}
                    </center><BR>
                    """, 
                    unsafe_allow_html=True
                )

                with st.expander(t("Check MLB Schedule"), expanded=False):
                    cola, _ = st.columns([1, 3])

                    game_year = cola.selectbox(
                        t("MLB Game Schedule"), 
                        ['2023', '2024', '2025'], 
                        index=1
                    )
                    
                    mlb_stats_api = MLBStatsAPI()

                    st.dataframe(
                        mlb_stats_api.get_mlb_season_schedule(game_year),
                        use_container_width=True,
                        hide_index=True
                    )

    else:
        try:
            firebase_credentials = credentials.Certificate(
                    "config/firebase_service_account_key.json"
                )
            firebase_admin.initialize_app(firebase_credentials)

        except: pass

        _, cola, _ = st.columns([1, 2, 1])

        with cola:
            st.markdown("<BR><center><H2> Welcome to PlayBook Live</H2></center>", unsafe_allow_html=True)

            with st.form(key='_form_login'):
                email = st.text_input('EMail/Username', placeholder='Username', label_visibility='collapsed')
                password = st.text_input('Password', placeholder='Password', label_visibility='collapsed', type="password")

                if st.session_state.username is False:
                    warning_message = st.warning("Invalid Username or Password")
                    time.sleep(3)
                    st.session_state.username = None
                    warning_message.empty()

                _, colx, _ = st.columns([1, 2, 1])

                with colx:
                    button_login = st.form_submit_button("LogIn to PlayBook Live", use_container_width=True)
                        
                if button_login:
                    try:
                        api_key = st.secrets['FIREBASE_WEB_API_KEY']
                        base_url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

                        if "@" not in email:
                            username = email
                            user = firebase_admin.auth.get_user(username)
                            email = user.email

                        data = {"email": email, "password": password}

                        response = requests.post(
                            base_url.format(api_key=api_key), json=data
                        )

                        if response.status_code == 200:
                            data = response.json()

                            if "user_display_name" not in st.session_state:
                                st.session_state.user_display_name = data["displayName"]
                                
                            st.session_state.user_display_name = data["displayName"]
                            st.session_state.username = firebase_admin.auth.get_user_by_email(email).uid

                            st.rerun()
                    
                        else:
                            st.session_state.username = False
                            st.rerun()

                    except Exception as error:
                        st.session_state.username = False
                        st.rerun()


            st.markdown(" ", unsafe_allow_html=True)

            _, colx, _ = st.columns([1, 2, 1])

            with colx:
                if st.button("New Here? Create an Account", use_container_width=True, type='tertiary'):
                    create_account()
