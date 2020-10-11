from flask import Flask, request
import json
import requests
import os
import praw

app = Flask(__name__)

PAT = os.environ.get("FACEBOOK_TOKEN")


@app.route("/", methods=["GET"])
def handle_verification():
    print("Handling Verification.")
    if (
        request.args.get("hub.verify_token", "")
        == "my_voice_is_my_password_verify_me"
    ):
        print("Verification successful!")
        return request.args.get("hub.challenge", "")
    else:
        print("Verification failed!")
        return "Error, wrong validation token"


@app.route("/", methods=["POST"])
def handle_messages():
    print("Handling Messages")
    payload = request.get_data()
    print(payload)
    for sender, message in messaging_events(payload):
        print("Incoming from %s: %s" % (sender, message))
        send_message(PAT, sender, message)
        return "ok"


def messaging_events(payload):
    """Generate tuples of (sender_id, message_text) from the
    provided payload.
    """
    data = json.loads(payload)
    messaging_events = data["entry"][0]["messaging"]
    for event in messaging_events:
        if "message" in event and "text" in event["message"]:
            yield event["sender"]["id"], event["message"]["text"].encode(
                "unicode_escape"
            )
        else:
            yield event["sender"]["id"], "I can't echo this"


def send_message(token, recipient, text):
    """Send the message text to recipient with id recipient."""

    if "meme" in text.lower():
        subreddit_name = "memes"
    elif "shower" in text.lower():
        subreddit_name = "Showerthoughts"
    elif "hmb" in text.lower():
        subreddit_name = "holdmybeer"
    elif "lotr" in text.lower():
        subreddit_name = "lotrmemes"
    elif "workspaces" in text.lower():
        subreddit_name = "Workspaces"
    elif "joke" in text.lower():
        subreddit_name = "Jokes"
    else:
        subreddit_name = "GetMotivated"

    if subreddit_name == "memes":
        for submission in reddit.subreddit(subreddit_name).hot(limit=None):
            payload = submission.url
            break
    if subreddit_name == "Showerthoughts":
        for submission in reddit.subreddit(subreddit_name).hot(limit=None):
            payload = submission.url
            break
    if subreddit_name == "holdmybeer":
        for submission in reddit.subreddit(subreddit_name).hot(limit=None):
            payload = submission.url
            break
    if subreddit_name == "lotrmemes":
        for submission in reddit.subreddit(subreddit_name).hot(limit=None):
            payload = submission.url
            break
    if subreddit_name == "Workspaces":
        for submission in reddit.subreddit(subreddit_name).hot(limit=None):
            payload = submission.url
            break
    if subreddit_name == "Jokes":
        for submission in reddit.subreddit(subreddit_name).hot(limit=None):
            payload = submission.url
            break
    if subreddit_name == "GetMotivated":
        for submission in reddit.subreddit(subreddit_name).hot(limit=None):
            payload = submission.url
            break

    r = requests.post(
        "https://graph.facebook.com/v3.3/me/messages",
        params={"access_token": token},
        data=json.dumps(
            {
                "recipient": {"id": recipient},
                "message": {
                    "attachment": {
                        "type": "image",
                        "payload": {"url": payload},
                    },
                },
            }
        ),
        headers={"Content-type": "application/json"},
    )
    if r.status_code != requests.codes.ok:
        print(r.text)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
