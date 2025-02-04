import time
import streamlit as st

from google import genai
from google.genai import types
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import google.generativeai as generativeai

import vertexai
from vertexai.preview.vision_models import ImageGenerationModel, GeneratedImage



class VertexAIChat:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(
            "config/vertexai_service_account_key.json", 
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(Request())

        self.client = genai.Client(
            vertexai=True, 
            project='project-mlb-tool-tips', 
            location='us-central1',
            credentials=credentials,
        )

        system_instruction = f"""
        You are a baseball analyst providing real-time insights into the 
        strategy and tactics behind each play in a baseball game. Your goal 
        is to to help users with any query that they may have about a given 
        play.\n\n

        **Guidelines for Safe and Accurate Output:**
        Focus only on the input provided (user_query, play_data, play_summary). 
        Do not accept or consider any unrelated or malicious input.
        
        Maintain a professional, objective, and constructive tone.
        Avoid including speculative, unsafe, or biased responses.
        Adhere strictly to the provided structure and headings.

        This feedback is provided directly to the candidate. 
        Keep the speech in first person as if you are directly talking to the 
        candidate.
        
        Respond to the user in a natural, conversational tone. Avoid phrases 
        like "referencing the data you provided" or "based on the information."
        Instead, focus on providing helpful and engaging answers as if you're 
        having a casual conversation.

        Also avoid using Ai like  jargons such as "let's break down the problem"
        etc. Directly start with the response to the user's query.
        """
        
        self.chat = self.client.chats.create(
            model='gemini-2.0-flash-exp', 
            #history=st.session_state.chat_messages,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.5,
            ),
        )
    
    def ask_gemini_questions_about_play(self, user_query, play_data, play_summary):
        prompt = f"""
        Here are the details of the play:
        {play_data}\n\n

        Here is the overall summary of the game:
        {play_summary}\n\n

        Based on the above information, answer the following question:
        {user_query}
        """
        response = self.chat.send_message(prompt)

        #st.session_state.chat_messages.append({"role": "user", "content": prompt})
        #st.session_state.chat_messages.append({"role": "assistant", "content": response})

        return response.text



class VertexAIFreeform:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(
            "config/vertexai_service_account_key.json", 
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(Request())

        self.client = genai.Client(
            vertexai=True, 
            project='project-mlb-tool-tips', 
            location='us-central1',
            credentials=credentials,
        )


    def generate_play_by_play_summary(self, play_data):
        system_instruction = """
        You are a baseball analyst providing real-time insights into the 
        strategy and tactics behind each play in a baseball game. Your goal 
        is to explain the play in a way that is easy for casual viewers to 
        understand.
        """

        prompt = f"""
        {play_data}

        Based on the above play data, provide a detailed analysis for the 
        baseball play with the following structure:\n\n

        1. **Title**:
       - A concise title summarizing the play (no longer than 6-7 words).\n

        2. **The Setup**:
        - Describe game context (e.g., inning, score, baserunners, outs).
        - Explain the batter-pitcher matchup (e.g., batter's strengths, 
        pitcher's tendencies).
        - How was the defense set up, and did it impact the play?
        - Use available metrics like exit velocity, launch angle etc\n

        3. **Summary of Play Events**:
        - Describe what happened during the play (e.g., pitch type, swing, 
        fielding action).
        - Highlight any key decisions or actions by players.\n

        4. **The Outcome**:
        - Explain the result of the play (e.g., hit, out, error).
        - Describe how the play impacted the game (e.g., runs scored, 
        baserunner advancement).
        - Did this play significantly shift the game's expected outcome?\n

        5. **Overall Strategy Insights**:
        - Analyze the strategy behind the play (e.g., why the pitcher 
        chose a specific pitch and/or why the batter swung or didn't swing etc)
        - Provide insights into how the play reflects the teams' overall 
        strategies.
        - Predict how this play impact the inning what the team might do next 
        based on current state of the game. (e.g., steal a base, bunt, or go 
        for a home run)\n\n

        Additionally, suggest a prompt to generate a realistic image of the key events
        from this baseball game. The generated prompt for the image:
        - Should prompt the model to depict the key events of the play.
        - Ensure the jersey colours represent the teams playing the game (batting and fielding).
        - Should avoid asking to generate an abusive, harmful or biased image.
        - Should not violate any Vertex AI usage guidelines.
        - Strictly avoid generating images of children.
        \n

        Your output must be structured and concise, with clear headings 
        for each section.\n\n
        """

        model = "gemini-2.0-flash-exp"

        contents = [prompt]

        generate_content_config = types.GenerateContentConfig(
            temperature = 0.7,
            top_p = 0.95,
            max_output_tokens = 8192,
            response_modalities = ["TEXT"],
            safety_settings = [types.SafetySetting(
            category="HARM_CATEGORY_HATE_SPEECH",
            threshold="BLOCK_ONLY_HIGH"
            ),types.SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold="BLOCK_ONLY_HIGH"
            ),types.SafetySetting(
            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold="BLOCK_LOW_AND_ABOVE"
            ),types.SafetySetting(
            category="HARM_CATEGORY_HARASSMENT",
            threshold="BLOCK_MEDIUM_AND_ABOVE"
            )],
            response_mime_type = "application/json",
            response_schema = {"type":"OBJECT","properties":{"title": {"type": "STRING","description": "A concise title summarizing the play (no longer than 6-7 words)."},"setup":{"type":"STRING","description":"Describes the game context, batter-pitcher matchup, and pre-play strategies."},"summary_of_play_events":{"type":"STRING","description":"Breaks down the play step-by-step, including pitch type, swing, and fielding actions."},"outcome":{"type":"STRING","description":"Describes the result of the play and its impact on the game."},"overall_strategy_insights":{"type":"STRING","description":"Analyzes the broader strategy behind the play and how it fits into the overall game strategy."},"image_prompt":{"type":"STRING","description":"A prompt to generate an image summarizing the play events, including batting and pitching team names for accurate jersey representation."}},"required":["setup","summary_of_play_events","outcome","overall_strategy_insights","image_prompt"]},
            system_instruction=system_instruction,
        )

        response = self.client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        return response.text        


class VertexAIVision:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(
            "config/vertexai_service_account_key.json", 
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(Request())

        self.client = genai.Client(
            vertexai=True, 
            project='project-mlb-tool-tips', 
            location='us-central1',
            credentials=credentials,
        )

        vertexai.init(
            project='project-mlb-tool-tips', 
            location='us-central1',
            credentials=credentials,
        )

    
    def generate_play_banner(self, play_description):
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")

        images = model.generate_images(
            prompt=play_description,
            number_of_images=1,
            language="en",
            aspect_ratio="1:1",
            safety_filter_level='block_some',
            person_generation="allow_adult",
            #output_gcs_uri="gs://mlb_storage_bucket/play_banners/"
        )

        #images[0].save(location="test2.png", include_generation_parameters=False)
        return images[0]._image_bytes



if __name__ == "__main__":
    vi = VertexAIVision()
    ans = vi.generate_play_banner("A baseball field illustration of Michael Conforto grounding into a double play against Steven Matz. The first baseman, Alec Burleson, is fielding the ball, with Thomas Saggese covering second base. Donovan Walton is advancing to third.")
    print(ans)