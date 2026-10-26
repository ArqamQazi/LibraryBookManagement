
from flask import Flask, render_template, request, redirect, url_for, flash
from database import get_connection, initialize_database
from datetime import date, timedelta

app = Flask(__name__)
app.secret_key = "library-secret-key"

initialize_database()


@app.route("/")
def home():
    connection = get_connection()

    books = connection.execute(
        "SELECT * FROM books ORDER BY title"
    ).fetchall()

    connection.close()

    return render_template("index.html", books=books)


@app.route("/add", methods=["POST"])
def add_book():
    isbn = request.form.get("isbn", "").strip()
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()

    if not isbn or not title or not author:
        flash("Please fill in all book details.")
        return redirect(url_for("home"))

    connection = get_connection()

    try:
        connection.execute(
            "INSERT INTO books (isbn, title, author) VALUES (?, ?, ?)",
            (isbn, title, author)
        )
        connection.commit()
        flash("Book added successfully!")
    except Exception:
        flash("A book with this ISBN already exists.")
    finally:
        connection.close()

    return redirect(url_for("home"))


@app.route("/search")
def search_books():
    keyword = request.args.get("q", "").strip()

    connection = get_connection()
    books = connection.execute(
        """
        SELECT * FROM books
        WHERE title LIKE ? OR author LIKE ?
        ORDER BY title
        """,
        (f"%{keyword}%", f"%{keyword}%")
    ).fetchall()
    connection.close()

    return render_template("index.html", books=books, keyword=keyword)


@app.route("/members", methods=["GET", "POST"])
def members():
    connection = get_connection()

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if name:
            connection.execute(
                "INSERT INTO members (name) VALUES (?)", (name,)
            )
            connection.commit()
            flash("Member added successfully!")

    member_list = connection.execute(
        "SELECT * FROM members ORDER BY name"
    ).fetchall()

    connection.close()
    return render_template("members.html", members=member_list)


@app.route("/issue", methods=["GET", "POST"])
def issue_book():
    connection = get_connection()

    if request.method == "POST":
        book_id = request.form.get("book_id", type=int)
        member_id = request.form.get("member_id", type=int)

        book = connection.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()

        member = connection.execute(
            "SELECT * FROM members WHERE id = ?", (member_id,)
        ).fetchone()

        if not book or not member:
            flash("Please select a valid book and member.")
        elif not book["available"]:
            flash("This book is already issued.")
        else:
            active_loans = connection.execute(
                """
                SELECT COUNT(*) AS total FROM loans
                WHERE member_id = ? AND return_date IS NULL
                """,
                (member_id,)
            ).fetchone()["total"]

            if active_loans >= 3:
                flash("A member cannot borrow more than 3 books.")
            else:
                issue_date = date.today()
                due_date = issue_date + timedelta(days=14)

                connection.execute(
                    """
                    INSERT INTO loans
                    (book_id, member_id, issue_date, due_date)
                    VALUES (?, ?, ?, ?)
                    """,
                    (book_id, member_id, issue_date.isoformat(),
                     due_date.isoformat())
                )

                connection.execute(
                    "UPDATE books SET available = 0 WHERE id = ?",
                    (book_id,)
                )
                connection.commit()
                flash("Book issued successfully!")

    books = connection.execute(
        "SELECT * FROM books WHERE available = 1 ORDER BY title"
    ).fetchall()

    member_list = connection.execute(
        "SELECT * FROM members ORDER BY name"
    ).fetchall()

    connection.close()

    return render_template(
        "issue.html", books=books, members=member_list
    )


@app.route("/loans")
def loans():
    connection = get_connection()

    loan_list = connection.execute(
        """
        SELECT loans.*, books.title, members.name
        FROM loans
        JOIN books ON loans.book_id = books.id
        JOIN members ON loans.member_id = members.id
        WHERE loans.return_date IS NULL
        ORDER BY loans.due_date
        """
    ).fetchall()

    connection.close()
    return render_template("loans.html", loans=loan_list)


@app.route("/return/<int:loan_id>", methods=["POST"])
def return_book(loan_id):
    connection = get_connection()

    loan = connection.execute(
        "SELECT * FROM loans WHERE id = ? AND return_date IS NULL",
        (loan_id,)
    ).fetchone()

    if loan:
        today = date.today()
        due_date = date.fromisoformat(loan["due_date"])
        late_days = max(0, (today - due_date).days)
        fine = late_days * 5

        connection.execute(
            """
            UPDATE loans SET return_date = ?, fine = ?
            WHERE id = ?
            """,
            (today.isoformat(), fine, loan_id)
        )

        connection.execute(
            "UPDATE books SET available = 1 WHERE id = ?",
            (loan["book_id"],)
        )

        connection.commit()
        flash(f"Book returned. Late fine: Rs. {fine}")
    else:
        flash("Active loan not found.")

    connection.close()
    return redirect(url_for("loans"))


if __name__ == "__main__":
    app.run(debug=True)
