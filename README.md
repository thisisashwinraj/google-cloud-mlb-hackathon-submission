# Google Cloud x MLB(TM) Hackathon – Building with Gemini Models

## Challenge
**Personalized Fan Highlights:** Build a system that allows fans to select team(s), player(s), etc. to follow and create audio, video, and/or text digests that fans could receive on a regular cadence to stay up on the latest highlights and commentary. Ensure your solution supports fans who speak English, Spanish, and Japanese. 

## Solution
MLB PlayBook Live revolutionizes the baseball fan experience by providing a comprehensive platform for exploring both current and classic MLB games.  Users can access real-time scores, dive deep into play-by-play breakdowns, analyze team lineups (including historical player data), and relive key moments.  A unique feature is the integration of Gemini, allowing users to ask questions about specific plays and receive AI-powered insights.  Furthermore, the platform offers multi-language support, making it accessible to a global audience.  All of this is presented in a user-friendly interface, enhanced by AI-generated images, offering a truly engaging and informative baseball experience.

The platform is built on a robust and scalable Google Cloud infrastructure. I leveraged Firebase Authentication for secure user management, storing non-sensitive user data in Cloud SQL. Game data and summaries are efficiently stored and managed using Firestore and Cloud Storage. Imagen 3 on Vertex AI powers the generation of dynamic, game-related images. The heart of my AI-driven insights is Gemini, which provides answers to user queries about plays and strategies. Finally, the Google Cloud Translation API enables seamless multi-language support, ensuring a global reach for my application. The front-end is built using Streamlit, providing an interactive and responsive user experience.
