import os
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session,sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    read = csv.reader(f)
    id=0
    for isbn,title,author,year in read:
        db.execute("insert into books (id, isbn, title, author, year) values (:id, :isbn, :title, :author, :year)",
                    {"id": id, "isbn": isbn, "title": title, "author": author, "year": year})
        id+=1
        print(f"added {id},{isbn}, {title},{author},{year}")
    db.commit()

if __name__=="__main__":
    main()