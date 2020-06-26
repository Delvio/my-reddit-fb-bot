import json
import os

import praw
import requests
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
import re

app = Flask(__name__)


uri = os.getenv("DATABASE_URL")  # or other relevant config var
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
# rest of connection code using the connection string `uri`

app.config["SQLALCHEMY_DATABASE_URI"] = uri
db = SQLAlchemy(app)

relationship_table = db.Table(
    "relationship_table",
    db.Column(
        "user_id", db.Integer, db.ForeignKey("users.id"), nullable=False
    ),
    db.Column(
        "post_id", db.Integer, db.ForeignKey("posts.id"), nullable=False
    ),
    db.PrimaryKeyConstraint("user_id", "post_id"),
)

PAT = os.environ.get("FACEBOOK_TOKEN")
reddit = praw.Reddit(
    client_id=os.environ.get("REDDIT_CLIENT_ID"),
    client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
    user_agent="my user agent",
)


def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    posts = db.relationship(
        "Posts", secondary=relationship_table, backref="users"
    )

    def __init__(self, name):
        self.name = name


class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    url = db.Column(db.String, nullable=False)

    def __init__(self, name, url):
        self.name = name
        self.url = url


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


quick_replies_list = [
    {
        "content_type": "text",
        "title": "Meme",
        "payload": "meme",
    },
    {
        "content_type": "text",
        "title": "Motivation",
        "payload": "motivation",
    },
    {
        "content_type": "text",
        "title": "Shower Thought",
        "payload": "Shower_Thought",
    },
    {
        "content_type": "text",
        "title": "Jokes",
        "payload": "Jokes",
    },
]


def send_message(token, recipient, text):
    """Send the message text to recipient with id recipient."""
    decoded_text = text.decode("utf-8")
    if "meme" in decoded_text.lower():
        subreddit_name = "memes"
    elif "shower" in decoded_text.lower():
        subreddit_name = "Showerthoughts"
    elif "hmb" in decoded_text.lower():
        subreddit_name = "holdmybeer"
    elif "lotr" in decoded_text.lower():
        subreddit_name = "lotrmemes"
    elif "workspaces" in decoded_text.lower():
        subreddit_name = "Workspaces"
    elif "joke" in decoded_text.lower():
        subreddit_name = "Jokes"
    else:
        subreddit_name = "GetMotivated"

    myUser = get_or_create(db.session, Users, name=recipient)

    if (subreddit_name == "Showerthoughts") or (
        subreddit_name == "holdmybeer"
    ):
        # for subreddits without flairs
        for submission in reddit.subreddit(subreddit_name).hot(limit=None):
            if submission.is_self == True:
                query_result = Posts.query.filter(
                    Posts.name == submission.id
                ).first()
                if query_result is None:
                    myPost = Posts(submission.id, submission.title)
                    myUser.posts.append(myPost)
                    db.session.commit()
                    payload = submission.title
                    break
                elif myUser not in query_result.users:
                    myUser.posts.append(query_result)
                    db.session.commit()
                    payload = submission.title
                    break
                else:
                    continue
        r = requests.post(
            "https://graph.facebook.com/v2.6/me/messages",
            params={"access_token": token},
            data=json.dumps(
                {
                    "recipient": {"id": recipient},
                    "message": {
                        "text": payload,
                        "quick_replies": quick_replies_list,
                    }
                    # "message": {"text": text.decode('unicode_escape')}
                }
            ),
            headers={"Content-type": "application/json"},
        )
    elif (
        (subreddit_name == "lotrmemes")
        or (subreddit_name == "Workspaces")
        or (subreddit_name == "Jokes")
    ):
        # for subreddits with certain flairs approved
        approved_flairs = [
            "HRAAAAH :scarybilbo::scarybilbo::scarybilbo::scarybilbo:",
            "CAST IT INTO THE FIRE :castintofire:",
            ":borthink:",
            "One does not simply walk in :boromir:" "No :No:",
            ":rohan: Rohan :rohan:",
            "The Hobbit",
            ":shocked:",
            "Keep your secrets :secrets:",
            "Crossover",
            "Repost :proudfoot:",
            "Shitpost",
            "Lord of the Rings",
            ":fingerguns:",
            "Original Content",
            None,
        ]
        for submission in reddit.subreddit(subreddit_name).hot(limit=None):
            if (submission.is_self == True) and (
                submission.link_flair_text in approved_flairs
            ):
                query_result = Posts.query.filter(
                    Posts.name == submission.id
                ).first()
                if query_result is None:
                    myPost = Posts(submission.id, submission.title)
                    myUser.posts.append(myPost)
                    db.session.commit()
                    payload = submission.title
                    payload_text = submission.selftext
                    break
                elif myUser not in query_result.users:
                    myUser.posts.append(query_result)
                    db.session.commit()
                    payload = submission.title
                    payload_text = submission.selftext
                    break
                else:
                    continue
        r = requests.post(
            "https://graph.facebook.com/v2.6/me/messages",
            params={"access_token": token},
            data=json.dumps(
                {
                    "recipient": {"id": recipient},
                    "message": {
                        "text": payload_text,
                        "quick_replies": quick_replies_list,
                    }
                    # "message": {"text": text.decode('unicode_escape')}
                }
            ),
            headers={"Content-type": "application/json"},
        )
    else:
        payload = "http://imgur.com/WeyNGtQ.jpg"
        for submission in reddit.subreddit(subreddit_name).hot(limit=None):
            if (submission.link_flair_css_class == "image") or (
                (submission.is_self != True)
                and ((".jpg" in submission.url) or (".png" in submission.url))
            ):
                query_result = Posts.query.filter(
                    Posts.name == submission.id
                ).first()
                if query_result is None:
                    myPost = Posts(submission.id, submission.url)
                    myUser.posts.append(myPost)
                    db.session.commit()
                    payload = submission.url
                    break
                elif myUser not in query_result.users:
                    myUser.posts.append(query_result)
                    db.session.commit()
                    payload = submission.url
                    break
                else:
                    continue
        r = requests.post(
            "https://graph.facebook.com/v2.6/me/messages",
            params={"access_token": token},
            data=json.dumps(
                {
                    "recipient": {"id": recipient},
                    "message": {
                        "attachment": {
                            "type": "image",
                            "payload": {"url": payload},
                        },
                        "quick_replies": quick_replies_list,
                    }
                    # "message": {"text": text.decode('unicode_escape')}
                }
            ),
            headers={"Content-type": "application/json"},
        )
    if r.status_code != requests.codes.ok:
        print(r.text)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
