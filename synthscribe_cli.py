import os
import json
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Union

# For OpenAI:
from openai import OpenAI

# For Anthropic (commented out until needed):
# from anthropic import Anthropic

# New imports for configuration, logging, and A/B testing
from config import get_config, Config
from logger import get_logger, log_performance
from ab_testing import ABTestingManager, PROMPT_VARIANTS

# Initialize configuration, logging, and A/B testing
config = get_config()
logger = get_logger()
ab_manager = ABTestingManager()

# Configuration is now handled by the config system

# User preferences storage
USER_PREFERENCES_FILE = "user_preferences.json"


class MusicSuggestion:
    """Class to represent a music suggestion."""

    def __init__(
        self,
        genre: str,
        artists: Optional[List[str]] = None,
        album: Optional[str] = None,
        album_artist: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.genre = genre
        self.artists = artists or []
        self.album = album
        self.album_artist = album_artist
        self.description = description

    def __str__(self) -> str:
        """String representation of the suggestion."""
        result = f"- Genre: {self.genre}\\n"
        if self.artists:
            result += f"  Artists: {', '.join(self.artists)}\\n"
        if self.album and self.album_artist:
            result += f"  Album: {self.album} by {self.album_artist}\\n"
        elif self.album:
            result += f"  Album: {self.album}\\n"
        if self.description:
            result += f"  Note: {self.description}\\n"
        return result

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "genre": self.genre,
            "artists": self.artists,
            "album": self.album,
            "album_artist": self.album_artist,
            "description": self.description,
        }


class UserProfile:
    """Class to manage user preferences and history."""

    def __init__(self):
        self.preferences = self._load_preferences()

    def _load_preferences(self) -> Dict:
        """Load user preferences from file."""
        try:
            if os.path.exists(USER_PREFERENCES_FILE):
                with open(USER_PREFERENCES_FILE, "r") as f:
                    return json.load(f)
            return {"history": [], "favorites": [], "feedback": {}}
        except Exception as e:
            print(f"Error loading preferences: {e}")
            return {"history": [], "favorites": [], "feedback": {}}

    def save_preferences(self):
        """Save user preferences to file."""
        try:
            with open(USER_PREFERENCES_FILE, "w") as f:
                json.dump(self.preferences, f, indent=2)
        except Exception as e:
            print(f"Error saving preferences: {e}")

    def add_to_history(self, mood: str, suggestions: List[MusicSuggestion]):
        """Add a mood and suggestions to history."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "mood": mood,
            "suggestions": [s.to_dict() for s in suggestions],
        }
        self.preferences["history"].insert(0, entry)
        # Keep history at a reasonable size
        if len(self.preferences["history"]) > 20:
            self.preferences["history"] = self.preferences["history"][:20]
        self.save_preferences()

    def add_to_favorites(self, suggestion: MusicSuggestion):
        """Add a suggestion to favorites."""
        # Avoid duplicates
        if not any(
            fav["genre"] == suggestion.genre and fav.get("album") == suggestion.album
            for fav in self.preferences["favorites"]
        ):
            self.preferences["favorites"].append(suggestion.to_dict())
            self.save_preferences()
            print(f"Added '{suggestion.genre}' to favorites.")
        else:
            print(f"'{suggestion.genre}' is already in favorites.")

    def add_feedback(self, mood: str, suggestion_idx: int, rating: int):
        """Add feedback for a suggestion (placeholder for now)."""
        # This is a placeholder. Actual feedback mechanism (like/dislike) could be more complex
        if mood not in self.preferences["feedback"]:
            self.preferences["feedback"][mood] = {}
        self.preferences["feedback"][mood][
            str(suggestion_idx)
        ] = rating  # Example: rating could be 1 for like, -1 for dislike
        self.save_preferences()
        print(
            f"Feedback recorded for suggestion {suggestion_idx + 1} for mood '{mood}'."
        )


def get_user_vybe_description() -> str:
    """Prompts the user for their current mood or task."""
    description = input("Describe your current vybe, mood, or task: ")
    return description


def parse_llm_suggestions(raw_suggestions: str) -> List[MusicSuggestion]:
    """Parse the LLM output into structured suggestions."""
    suggestions: List[MusicSuggestion] = []
    current_data: Dict[str, Union[str, List[str]]] = {}

    # Split suggestions based on a common pattern like "- Genre:" or "* Genre:"
    # This regex looks for a bullet point (-, *, •) followed by "Genre:"
    import re

    suggestion_blocks = re.split(r"(?=\n*[\-\*\•]\s*Genre:)", raw_suggestions.strip())

    for block in suggestion_blocks:
        if not block.strip():
            continue

        genre = ""
        artists = []
        album_title = None
        album_artist_name = None
        note = None

        lines = block.strip().split(
            "\\n"
        )  # Using literal \\n from __str__ if it appears
        if not lines:
            lines = block.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if (
                line.startswith("- Genre:")
                or line.startswith("* Genre:")
                or line.startswith("• Genre:")
            ):
                genre = line.split(":", 1)[1].strip()
            elif line.startswith("Artists:") or line.startswith(
                "Artist:"
            ):  # Handle " Artist:" singular
                artists_str = line.split(":", 1)[1].strip()
                artists = [
                    a.strip() for a in re.split(r",| and ", artists_str) if a.strip()
                ]  # Split by comma or 'and'
            elif line.startswith("Album:"):
                album_str = line.split(":", 1)[1].strip()
                if " by " in album_str:
                    album_title, album_artist_name = map(
                        str.strip, album_str.split(" by ", 1)
                    )
                else:
                    album_title = album_str
            elif line.startswith("Note:"):
                note = line.split(":", 1)[1].strip()

        if genre:  # Only add if we successfully parsed a genre
            suggestions.append(
                MusicSuggestion(
                    genre=genre,
                    artists=artists,
                    album=album_title,
                    album_artist=album_artist_name,
                    description=note,
                )
            )

    return suggestions


def analyze_user_history(user_profile: UserProfile) -> str:
    """Extract context from user history for persona-based prompts"""
    favorite_genres = {}
    for entry in user_profile.preferences.get("history", [])[:5]:  # Last 5 entries
        for suggestion in entry.get("suggestions", []):
            genre = suggestion.get("genre", "")
            if genre:
                favorite_genres[genre] = favorite_genres.get(genre, 0) + 1

    if favorite_genres:
        top_genres = sorted(favorite_genres.items(), key=lambda x: x[1], reverse=True)[
            :3
        ]
        return f"The user previously enjoyed: {', '.join([g[0] for g in top_genres])}"
    return ""


def create_enhanced_prompt(description: str, user_profile: UserProfile) -> str:
    """Create an enhanced prompt using user history and preferences."""
    favorite_genres_count: Dict[str, int] = {}
    favorite_artists_count: Dict[str, int] = {}

    for entry in user_profile.preferences.get("history", []):
        for suggestion_dict in entry.get("suggestions", []):
            genre = suggestion_dict.get("genre")
            if genre:
                favorite_genres_count[genre] = favorite_genres_count.get(genre, 0) + 1

            for artist in suggestion_dict.get("artists", []):
                if artist:  # Ensure artist is not an empty string
                    favorite_artists_count[artist] = (
                        favorite_artists_count.get(artist, 0) + 1
                    )

    top_genres = sorted(
        favorite_genres_count.items(), key=lambda x: x[1], reverse=True
    )[:3]
    top_artists = sorted(
        favorite_artists_count.items(), key=lambda x: x[1], reverse=True
    )[:3]

    context_parts = []
    if top_genres:
        context_parts.append(
            f"User has previously enjoyed genres like: {', '.join([g[0] for g in top_genres])}."
        )
    if top_artists:
        context_parts.append(
            f"User has previously enjoyed artists like: {', '.join([a[0] for a in top_artists])}."
        )

    context_str = " ".join(context_parts)
    if context_str:
        context_str = f"Historical context about the user: {context_str}"

    prompt = f"""
You are SynthScribe, a music recommendation expert.
A user needs music suggestions for the following situation: "{description}"
{context_str}

Please provide 3-4 distinct musical ideas. For each idea, strictly follow this format:
- Genre: [The specific genre or subgenre]
  Artists: [Comma-separated list of 1-2 representative artists, if applicable]
  Album: [Album Title] by [Album Artist] (Only include 'by [Album Artist]' if the album artist is distinct or particularly noteworthy. If no specific album, omit this line.)
  Note: [A brief, 1-sentence explanation of why this music matches the user's situation or preferences, or a unique characteristic of the suggestion. Be creative and insightful.]

Focus on variety if the user's description is broad, or specificity if it's narrow.
Aim for suggestions that are generally accessible and well-regarded.
Only provide the formatted suggestions. Do not include any conversational filler, apologies, or extra text before or after the list.
Example of a single suggestion:
- Genre: Instrumental Lofi Hip Hop
  Artists: Nujabes, J Dilla
  Album: Metaphorical Music by Nujabes
  Note: Perfect for focused work or study, with smooth beats and a relaxed atmosphere.
"""
    return prompt


@log_performance("get_music_suggestions")
def get_music_suggestions(
    description: str, api_key: str, user_profile: UserProfile
) -> List[MusicSuggestion]:
    """
    Sends the description to an LLM and returns structured music suggestions.
    """
    # Use config instead of global variables
    if config.llm.provider.value == "local":
        logger.logger.info(f"Using Local LLM ({config.llm.model_name}) via Ollama")
        client = OpenAI(
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
        )
        llm_model_name = config.llm.model_name
    else:
        logger.logger.info("Using OpenAI API")
        client = OpenAI(api_key=api_key)
        llm_model_name = config.llm.model_name

    # Generate request ID for tracking
    request_id = logger.log_request(
        user_id=user_profile.preferences.get("user_id", "anonymous"),
        mood=description,
        provider=config.llm.provider.value,
    )

    try:
        # Get A/B test variant if experiment is running
        variant_name = ab_manager.get_user_variant(
            "prompt_optimization", user_profile.preferences.get("user_id", "anonymous")
        )

        # Use variant-specific prompt if available
        if variant_name and variant_name in PROMPT_VARIANTS:
            prompt_template = PROMPT_VARIANTS[variant_name]["config"][
                "template"
            ].format(
                description=description,
                context=(
                    analyze_user_history(user_profile)
                    if variant_name == "persona_based"
                    else ""
                ),
            )
        else:
            # Fall back to your existing prompt
            prompt_template = create_enhanced_prompt(description, user_profile)

        # Log LLM call
        logger.log_llm_call(
            request_id=request_id,
            provider=config.llm.provider.value,
            model=llm_model_name,
            prompt_length=len(prompt_template),
        )

        start_time = time.time()

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful music recommendation assistant named SynthScribe.",
                },
                {"role": "user", "content": prompt_template},
            ],
            model=llm_model_name,
            max_tokens=config.llm.max_tokens,
            temperature=config.llm.temperature,
            timeout=config.llm.timeout,
        )

        duration_ms = (time.time() - start_time) * 1000
        suggestions_text = chat_completion.choices[0].message.content

        # Log response
        logger.log_llm_response(
            request_id=request_id,
            response_length=len(suggestions_text) if suggestions_text else 0,
            duration_ms=duration_ms,
        )

        if suggestions_text:
            parsed_suggestions = parse_llm_suggestions(suggestions_text.strip())

            # Log recommendations
            genres = [s.genre for s in parsed_suggestions]
            logger.log_recommendation(
                request_id=request_id,
                user_id=user_profile.preferences.get("user_id", "anonymous"),
                recommendation_count=len(parsed_suggestions),
                genres=genres,
            )

            return parsed_suggestions
        return []

    except Exception as e:
        logger.log_error(
            e, {"request_id": request_id, "phase": "llm_call", "mood": description}
        )
        print(f"Error communicating with AI: {e}")
        return []


def display_menu():
    """Display the main menu options."""
    print("\\n" + "=" * 40)
    print(f"SynthScribe v{config.version} - AI Music Mood Matcher")
    print("=" * 40)
    print(f"Provider: {config.llm.provider.value.title()} ({config.llm.model_name})")
    if config.features.enable_a_b_testing:
        print("A/B Testing: Enabled")
    print("=" * 40)
    print("1. Get music suggestions for your current mood")
    print("2. View your suggestion history (last 5)")
    print("3. Manage your favorites")
    print("4. Exit")
    print("=" * 40)
    return input("Select an option (1-4): ")


def view_history(user_profile: UserProfile):
    """Display the user's suggestion history."""
    history = user_profile.preferences.get("history", [])

    if not history:
        print("No history found.")
        input("\\nPress Enter to continue...")
        return

    print("\\n" + "=" * 40)
    print("Your Music Suggestion History (Last 5)")
    print("=" * 40)

    for i, entry in enumerate(history[:5]):
        print(f"\\n{i+1}. Mood: '{entry['mood']}'")
        dt_object = datetime.fromisoformat(entry["timestamp"])
        print(f"   Time: {dt_object.strftime('%Y-%m-%d %H:%M')}")
        print("   Suggestions:")
        for suggestion_dict in entry.get("suggestions", []):
            # Reconstruct MusicSuggestion object for display using its __str__ method
            suggestion = MusicSuggestion(
                genre=suggestion_dict.get("genre", "N/A"),
                artists=suggestion_dict.get("artists", []),
                album=suggestion_dict.get("album"),
                album_artist=suggestion_dict.get("album_artist"),
                description=suggestion_dict.get("description"),
            )
            # Indent each line of the suggestion string
            for line in str(suggestion).strip().split("\\n"):
                print(f"     {line}")

    input("\\nPress Enter to continue...")


def manage_favorites(user_profile: UserProfile):
    """Manage the user's favorite suggestions."""
    favorites = user_profile.preferences.get("favorites", [])

    if not favorites:
        print("No favorites found.")
        input("\\nPress Enter to continue...")
        return

    while True:
        print("\\n" + "=" * 40)
        print("Your Favorite Music Suggestions")
        print("=" * 40)

        for i, favorite_dict in enumerate(favorites):
            suggestion = MusicSuggestion(
                genre=favorite_dict.get("genre", "N/A"),
                artists=favorite_dict.get("artists", []),
                album=favorite_dict.get("album"),
                album_artist=favorite_dict.get("album_artist"),
                description=favorite_dict.get("description"),
            )
            suggestion_str = str(suggestion).strip().replace("\\n", "\\n   ")
            print(f"\\n{i+1}. {suggestion_str}")  # Compact display

        print("\\nOptions:")
        print("1. Remove a favorite")
        print("2. Return to main menu")

        choice = input("\\nSelect an option (1-2): ")

        if choice == "1":
            idx_str = input(
                "Enter the number of the favorite to remove (or 0 to cancel): "
            )
            try:
                idx_to_remove = int(idx_str)
                if idx_to_remove == 0:
                    continue
                idx_to_remove -= 1  # Adjust to 0-based index
                if 0 <= idx_to_remove < len(favorites):
                    removed = favorites.pop(idx_to_remove)
                    user_profile.save_preferences()
                    print(f"Removed: {removed.get('genre', 'N/A')}")
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Please enter a valid number.")
        elif choice == "2":
            break
        else:
            print("Invalid option. Please try again.")
    input("\\nPress Enter to continue...")


def handle_suggestions_interaction(
    suggestions: List[MusicSuggestion], user_profile: UserProfile, mood: str
):
    """Allow the user to interact with suggestions (e.g., add to favorites)."""
    if not suggestions:
        return

    print("\\nWould you like to save any of these suggestions to your favorites?")
    print("Enter the numbers (e.g., 1, 3 or 0 to skip): ")

    choice = input("> ").strip()
    if choice == "0" or not choice:
        return

    try:
        selected_indices = [
            int(idx.strip()) - 1 for idx in choice.split(",") if idx.strip()
        ]
        for idx in selected_indices:
            if 0 <= idx < len(suggestions):
                user_profile.add_to_favorites(suggestions[idx])

                # Record A/B testing success and feedback
                user_id = user_profile.preferences.get("user_id", "anonymous")
                variant_name = ab_manager.get_user_variant(
                    "prompt_optimization", user_id
                )
                if variant_name:
                    ab_manager.record_success("prompt_optimization", variant_name)
                    ab_manager.record_feedback(
                        "prompt_optimization", variant_name, 5.0
                    )  # High score for favorited items

                # Log user feedback
                logger.log_user_feedback(
                    user_id=user_id, genre=suggestions[idx].genre, rating=5.0
                )

                # Add to user feedback preferences
                user_profile.add_feedback(mood, idx, 1)  # 1 for like
            else:
                print(f"Invalid selection: {idx+1}. It's out of range.")
    except ValueError:
        print("Invalid input. Please enter numbers separated by commas (e.g., 1, 2).")


def main():
    """Main function to run the SynthScribe CLI tool."""
    # Show configuration on startup
    logger.logger.info(f"Starting SynthScribe v{config.version}")
    logger.logger.debug(f"Configuration: {config.to_dict()}")

    # Initialize user profile with a generated user_id
    user_profile = UserProfile()
    if "user_id" not in user_profile.preferences:
        user_profile.preferences["user_id"] = f"user_{uuid.uuid4().hex[:8]}"
        user_profile.save_preferences()

    # Initialize A/B test if not exists
    if "prompt_optimization" not in ab_manager.experiments:
        ab_manager.create_experiment(
            name="prompt_optimization",
            description="Testing different prompt strategies",
            variants=list(PROMPT_VARIANTS.values()),
        )

    # Determine API key to use
    api_key_to_use = config.llm.api_key
    if config.llm.provider.value != "local" and not config.llm.api_key:
        env_api_key = (
            os.getenv("OPENAI_API_KEY")
            if config.llm.provider.value == "openai"
            else os.getenv("ANTHROPIC_API_KEY")
        )
        if not env_api_key:
            print(
                f"Error: {config.llm.provider.value.upper()}_API_KEY not found in environment variables. Please set it to use {config.llm.provider.value.title()} API."
            )
            exit()
        api_key_to_use = env_api_key

    while True:
        choice = display_menu()

        if choice == "1":
            user_input = get_user_vybe_description()

            if user_input:
                # Show current configuration
                provider_display = (
                    f"{config.llm.provider.value.title()} ({config.llm.model_name})"
                )
                print(f"\\nUsing {provider_display} to think of some vybes for you...")

                suggestions = get_music_suggestions(
                    user_input, api_key_to_use, user_profile
                )

                if suggestions:
                    print("\\nHere are some ideas from SynthScribe:")
                    print("-" * 50)
                    for i, suggestion in enumerate(suggestions):
                        # Ensuring each line of the suggestion is printed correctly indented
                        suggestion_str = str(suggestion).strip()
                        lines = suggestion_str.split("\\n")
                        print(f"{i+1}. {lines[0]}")  # Print first line with number
                        for line in lines[1:]:
                            print(f"   {line}")  # Indent subsequent lines
                        print("-" * 10)  # Small separator between suggestions
                    print("-" * 50)

                    # Record A/B test impression (user saw the suggestions)
                    user_id = user_profile.preferences.get("user_id", "anonymous")
                    variant_name = ab_manager.get_user_variant(
                        "prompt_optimization", user_id
                    )
                    # Note: impression is already recorded in get_user_variant, but we could add additional tracking here

                    user_profile.add_to_history(user_input, suggestions)
                    handle_suggestions_interaction(
                        suggestions, user_profile, user_input
                    )
                else:
                    print(
                        "Sorry, couldn't generate any suggestions this time. The AI might be having an off day or the response was unparseable."
                    )
            else:
                print("No description provided. Let's try that again.")

        elif choice == "2":
            view_history(user_profile)

        elif choice == "3":
            manage_favorites(user_profile)

        elif choice == "4":
            print("\\nThank you for using SynthScribe! Goodbye.")
            break

        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()

# --- For Anthropic (Illustrative - adjust model name and exact API call) ---
# client = Anthropic(api_key=api_key)
# try:
#     prompt = f"""{anthropic.HUMAN_PROMPT}
#     You are SynthScribe... (similar prompt as above) ...
#     Based on this, please suggest 3-5 distinct musical ideas...
#     Their current situation is: "{description}"
#     Your suggestions:
#     {anthropic.AI_PROMPT}"""
#
#     completion = client.completions.create(
#         model="claude-2", # Or "claude-instant-1", etc.
#         max_tokens_to_sample=500,
#         prompt=prompt,
#     )
#     return completion.completion.strip()
# except Exception as e:
#     return f"Error communicating with AI: {e}"
#
# --- For other LLMs, adapt API call here ---
