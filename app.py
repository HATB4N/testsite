from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Database models
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45))
    text = db.Column(db.String(500))
    comments = db.relationship('Comment', backref='post', lazy=True)

    def __init__(self, ip, text):
        self.ip = ip
        self.text = text


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45))
    text = db.Column(db.String(500))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    def __init__(self, ip, text, post_id):
        self.ip = ip
        self.text = text
        self.post_id = post_id


# Create the database tables
with app.app_context():
    db.create_all()


def ip_blind(ip):
    return '.'.join(ip.split('.')[:2]) + '.x.x'


@app.route('/')
def index():
    user_ip = ip_blind(request.remote_addr)
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template('index.html', ip=user_ip, posts=posts)

@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, request.path[1:])



@app.route('/post', methods=['POST'])
def post_message():
    message_text = request.form.get('message')
    user_ip = ip_blind(request.remote_addr)
    if message_text:
        if message_text.strip().lower() == '/delete all':
            delete_all_messages()
        else:
            new_post = Post(ip=user_ip, text=message_text)
            db.session.add(new_post)
            db.session.commit()
    return redirect(url_for('index'))


@app.route('/comment/<int:post_id>', methods=['POST'])
def comment_post(post_id):
    comment_text = request.form.get('comment')
    user_ip = ip_blind(request.remote_addr)
    if comment_text:
        new_comment = Comment(ip=user_ip, text=comment_text, post_id=post_id)
        db.session.add(new_comment)
        db.session.commit()
    return redirect(url_for('index'))


def delete_all_messages():
    db.session.query(Post).delete()
    db.session.query(Comment).delete()
    db.session.commit()
    print("Deleted all posts and comments.")


if __name__ == '__main__':
    app.run()
