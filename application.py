import os, requests, json
from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"),pool_size=10, max_overflow=20)
db = scoped_session(sessionmaker(bind=engine))

def create_hash(n):
    f=2
    hashed = 0
    for i in n:
        hashed += ord(i) * f
        f+=1
    hashed = hashed^2
    hashed = str(hashed)
    return hashed

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method=="POST":
        return render_template("login.html")
    else:
        return render_template("login.html")

@app.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        username = db.execute("select username, password from users").fetchall()
        usrnm = request.form['username']
        paswrd = request.form['password']
        f=0
        for us in username:
            if usrnm==us.username:
                return render_template("login.html",headline="Username is taken.")    

        if len(paswrd) <6:
            return render_template("login.html",headline="Password must have minimum 6 letters.")

        paswrd = create_hash(paswrd)
        db.execute("insert into users (username, password) values(:usrnm,:paswrd)",
                    {"usrnm": usrnm, "paswrd": paswrd})
        db.commit()
        return render_template("login.html",headline="Successfully signed up.")
    
    else:
        return render_template("error.html", err = "Invalid method.")

@app.route("/home", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method=="POST":
        usrnm = request.form.get("username")
        paswrd = request.form.get("password")
        paswrd = create_hash(paswrd)
        user=db.execute("select * from users where username= :usrnm",
        {"usrnm": usrnm}).fetchone()
        if user is None:
            return render_template("login.html",headline="Invalid username.")

        if paswrd != user.password:
            return render_template("login.html",headline="Invalid password.")
        session["usr"]=user.id
        return render_template("home.html")
    else:
        return render_template("error.html", err = "Invalid method.")
    db.commit()

@app.route("/logout",methods=["GET", "POST"])
def logout():
    if 'usr' in session:
        session.pop('usr',None)
        return render_template("index.html")

@app.route("/search",methods=["POST","GET"])
def search():
    if request.method == "POST":
        name = request.form.get('search')
        if name is None:
            return render_template("home.html")
        name=name.lower()
        books = db.execute("select * from books").fetchall()
        book = []
        isbn = []
        n=0
        for i in books:
            if name in i.isbn or name == '%'+i.isbn+'%':
                book.append(f"{i.title} by {i.author} - {i.isbn}")
                isbn.append(i.isbn)
                n+=n
                continue
            
            if name in (i.title).lower() or name == '%'+(i.title).lower()+'%':
                book.append(f"{i.title} by {i.author} - {i.isbn}")
                isbn.append(i.isbn)
                n+=n
                continue
            
            if name in (i.author).lower() or name == '%'+i.author.lower()+'%':
                book.append(f"{i.title} by {i.author} - {i.isbn}")
                isbn.append(i.isbn)
                n+=n
                continue

        if not book:
            return render_template("search.html", err="No match found.")
        
        else:
            book=zip(book,isbn)
            return render_template("search.html", res=book)
        db.commit()
    
    else:
        return render_template("error.html", err = "Invalid method.")

@app.route("/book/<string:isbn>", methods=["POST","GET"])
def book(isbn):
    if book in session:
        session.pop("book",None)
    session["book"] = isbn
    info = db.execute("select * from books where isbn = :isbn", {"isbn":isbn}).fetchone()
    try:
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "OT2oBaEabBiJLpfBNPeEqA", "isbns": isbn})
        data = res.json()
        ttl_ratings = data['books'][0]['work_ratings_count']
        rating = data['books'][0]['average_rating']
        
    except json.decoder.JSONDecodeError:
        ttl_ratings = "Not available."
        rating = "Not available."

    title = info.title
    author = info.author
    revw=[]
    rev_usr=[]
    rat = 0
    year = info.year
    reviews = db.execute("select * from reviews where isbn = :isbn",{"isbn":isbn}).fetchall()
    if not reviews:
        return render_template("book.html", isbn=isbn, title=title, author=author, ratings=ttl_ratings, rating=rating, year=year, nreviews="No reviews posted.")

    for i in range(len(reviews)):
        r = db.execute("select username from users where id = :id",{"id":reviews[i].user_id}).fetchone()
        rev_usr.append(r.username)
        revw.append(reviews[i].review)
        rat += reviews[i].rating
    revw = zip(rev_usr,revw)

    wis_rating = rat/len(reviews)

    return render_template("book.html", wisdom_rating = wis_rating, isbn=isbn, title=title, author=author, ratings=ttl_ratings, rating=rating, year=year, reviews=revw)

@app.route("/review", methods=["POST","GET"])
def rev_post():
    if request.method=="POST":
        usr_id = session["usr"]
        book = session["book"]
        
        user_id = db.execute("select * from reviews where user_id = :usr and isbn = :book",{"usr": usr_id, "book": book}).fetchone()
        if user_id is not None:
            return redirect(url_for("book",isbn=book))

        rat = request.form['rate']
        rev = request.form['review']
        db.execute("insert into reviews (isbn, user_id, review, rating) values (:isbn, :usr, :review, :rate)",
                    {"isbn":book, "usr":usr_id, "review":rev, "rate": rat})     
        db.commit()
        
        return redirect(url_for("book",isbn=book))

    else:
        return render_template("error.html", err = "Invalid method.")

@app.route("/api/<string:isbn>", methods=["GET"])
def api(isbn):
    info = db.execute("select * from books where isbn = :isbn",{"isbn": isbn}).fetchone()
    if info is None:
        return jsonify({"N/A": "Not Available"}) 
    try:
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "OT2oBaEabBiJLpfBNPeEqA", "isbns": isbn})
        data = res.json()
        r_count = data["books"][0]["work_ratings_count"]
        avg_r = data["books"][0]["average_rating"]
    
    except json.decoder.JSONDecodeError:
        r_count = ""
        avg_r = ""
    isbn = info.isbn
    title = info.title
    author = info.author
    year = info.year

    return jsonify({
        "title": title,
        "author": author,
        "year": year,
        "isbn": isbn,
        "review_count": r_count,
        "average_score": avg_r
    })
