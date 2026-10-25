
import pytest
import database
from datetime import date, timedelta
from app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_database = tmp_path / "test_library.db"
    monkeypatch.setattr(database, "DATABASE", test_database)
    database.initialize_database()

    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


def test_homepage(client):
    response = client.get("/")
    assert response.status_code == 200


def test_add_book(client):
    response = client.post(
        "/add",
        data={
            "isbn": "TEST101",
            "title": "Python Basics",
            "author": "John Smith"
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Python Basics" in response.data


def test_duplicate_isbn(client):
    book_data = {
        "isbn": "TEST102",
        "title": "Python Basics",
        "author": "John Smith"
    }

    client.post("/add", data=book_data)

    response = client.post(
        "/add",
        data={
            "isbn": "TEST102",
            "title": "Python Advanced",
            "author": "Jane Smith"
        },
        follow_redirects=True
    )

    assert b"already exists" in response.data


def test_search_by_author(client):
    client.post(
        "/add",
        data={
            "isbn": "TEST103",
            "title": "Networking Basics",
            "author": "Alice Brown"
        }
    )

    response = client.get("/search?q=Alice")

    assert response.status_code == 200
    assert b"Networking Basics" in response.data


def test_search_by_title(client):
    client.post(
        "/add",
        data={
            "isbn": "TEST105",
            "title": "Python Programming",
            "author": "Alice Brown"
        }
    )

    response = client.get("/search?q=Python%20Programming")

    assert response.status_code == 200
    assert b"Python Programming" in response.data


def test_member_cannot_borrow_more_than_three_books(client):
    connection = database.get_connection()

    connection.execute(
        "INSERT INTO members (name) VALUES (?)",
        ("Test Member",)
    )
    member_id = connection.execute(
        "SELECT id FROM members"
    ).fetchone()["id"]

    for number in range(4):
        connection.execute(
            """
            INSERT INTO books (isbn, title, author, available)
            VALUES (?, ?, ?, 1)
            """,
            (f"LIMIT{number}", f"Book {number}", "Test Author")
        )

    connection.commit()

    books = connection.execute(
        "SELECT id FROM books ORDER BY id"
    ).fetchall()

    today = date.today()
    due_date = today + timedelta(days=14)

    for book in books[:3]:
        connection.execute(
            """
            INSERT INTO loans
            (book_id, member_id, issue_date, due_date)
            VALUES (?, ?, ?, ?)
            """,
            (
                book["id"],
                member_id,
                today.isoformat(),
                due_date.isoformat()
            )
        )
        connection.execute(
            "UPDATE books SET available = 0 WHERE id = ?",
            (book["id"],)
        )

    connection.commit()
    fourth_book_id = books[3]["id"]
    connection.close()

    response = client.post(
        "/issue",
        data={
            "book_id": fourth_book_id,
            "member_id": member_id
        },
        follow_redirects=True
    )

    assert b"cannot borrow more than 3 books" in response.data


def test_issued_book_cannot_be_issued_again(client):
    client.post(
        "/add",
        data={
            "isbn": "TEST104",
            "title": "Issued Book",
            "author": "Test Author"
        }
    )

    connection = database.get_connection()
    book = connection.execute(
        "SELECT id FROM books WHERE isbn = ?",
        ("TEST104",)
    ).fetchone()

    connection.execute(
        "INSERT INTO members (name) VALUES (?)",
        ("Test Member",)
    )
    member = connection.execute(
        "SELECT id FROM members"
    ).fetchone()

    connection.commit()
    connection.close()

    issue_data = {
        "book_id": book["id"],
        "member_id": member["id"]
    }

    client.post("/issue", data=issue_data)

    response = client.post(
        "/issue",
        data=issue_data,
        follow_redirects=True
    )

    assert b"This book is already issued." in response.data


def test_late_fine_is_five_rupees_per_day(client):
    connection = database.get_connection()

    connection.execute(
        """
        INSERT INTO books (isbn, title, author, available)
        VALUES (?, ?, ?, 0)
        """,
        ("FINE101", "Fine Test Book", "Test Author")
    )
    book_id = connection.execute(
        "SELECT id FROM books"
    ).fetchone()["id"]

    connection.execute(
        "INSERT INTO members (name) VALUES (?)",
        ("Fine Test Member",)
    )
    member_id = connection.execute(
        "SELECT id FROM members"
    ).fetchone()["id"]

    today = date.today()
    due_date = today - timedelta(days=15)
    issue_date = due_date - timedelta(days=14)

    connection.execute(
        """
        INSERT INTO loans
        (book_id, member_id, issue_date, due_date)
        VALUES (?, ?, ?, ?)
        """,
        (
            book_id,
            member_id,
            issue_date.isoformat(),
            due_date.isoformat()
        )
    )

    loan_id = connection.execute(
        "SELECT id FROM loans"
    ).fetchone()["id"]

    connection.commit()
    connection.close()

    client.post(f"/return/{loan_id}")

    connection = database.get_connection()
    loan = connection.execute(
        "SELECT fine FROM loans WHERE id = ?",
        (loan_id,)
    ).fetchone()
    connection.close()

    assert loan["fine"] == 75
