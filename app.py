from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
import math
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")


# =========================================================
# POSTGRESQL CONNECTION
# =========================================================

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432")
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# GPS / LOCATION
# =========================================================

@app.route("/location")
def location():
    return render_template("location.html")


# =========================================================
# MAP / NEARBY PARKING
# =========================================================

@app.route("/nearby-parking")
def nearby_parking():
    return render_template("nearby_parking.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, fullname, username, password
            FROM users
            WHERE LOWER(username) = LOWER(%s)
        """, (username,))

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user is not None and str(user[3]) == password:

            session["user_id"] = user[0]
            session["username"] = user[2]

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid Username or Password."
        )

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))



# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form.get(
            "fullname", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip()

        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get(
            "password", ""
        ).strip()

        confirm_password = request.form.get(
            "confirm_password", ""
        ).strip()

        # CHECK PASSWORD MATCH
        if password != confirm_password:
            return """
            <script>
                alert("Passwords do not match!");
                window.location.href="/register";
            </script>
            """

        conn = get_db_connection()
        cursor = conn.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO users
                (
                    fullname,
                    email,
                    username,
                    password
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    fullname,
                    email,
                    username,
                    password
                )
            )

            conn.commit()

        except psycopg2.errors.UniqueViolation:

            conn.rollback()

            return "Username or Email already exists."

        finally:
            cursor.close()
            conn.close()

        return redirect(
            url_for("registration_success")
        )

    return render_template("register.html")


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        new_password = request.form.get(
            "new_password",
            ""
        ).strip()

        confirm_password = request.form.get(
            "confirm_password",
            ""
        ).strip()

        # -------------------------------------------------
        # CHECK EMPTY FIELDS
        # -------------------------------------------------

        if not username or not new_password or not confirm_password:

            return """
            <script>
                alert("Please fill all fields!");
                window.location.href="/forgot-password";
            </script>
            """

        # -------------------------------------------------
        # CHECK PASSWORD MATCH
        # -------------------------------------------------

        if new_password != confirm_password:

            return """
            <script>
                alert("Passwords do not match!");
                window.location.href="/forgot-password";
            </script>
            """

        # -------------------------------------------------
        # DATABASE CONNECTION
        # -------------------------------------------------

        conn = get_db_connection()
        cursor = conn.cursor()

        # -------------------------------------------------
        # CHECK USERNAME
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(username) = LOWER(%s)
            """,
            (username,)
        )

        user = cursor.fetchone()

        if user is None:

            cursor.close()
            conn.close()

            return """
            <script>
                alert("Username not found!");
                window.location.href="/forgot-password";
            </script>
            """

        # -------------------------------------------------
        # UPDATE PASSWORD
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE users
            SET password = %s
            WHERE id = %s
            """,
            (
                new_password,
                user[0]
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        return """
        <script>
            alert("Password reset successfully!");
            window.location.href="/login";
        </script>
        """

    return render_template(
        "forgot_password.html"
    )


# =========================================================
# REGISTRATION SUCCESS
# =========================================================

@app.route("/registration-success")
def registration_success():

    return render_template(
        "registration_success.html"
    )


# =========================================================
# VEHICLE MANAGEMENT
# =========================================================

@app.route("/vehicles", methods=["GET", "POST"])
def vehicles():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    if request.method == "POST":

        vehicle_number = request.form.get(
            "vehicle_number", ""
        ).strip()

        vehicle_type = request.form.get(
            "vehicle_type", ""
        ).strip()

        if vehicle_number and vehicle_type:

            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                cursor.execute(
                    """
                    INSERT INTO vehicles
                    (
                        user_id,
                        vehicle_number,
                        vehicle_type
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        user_id,
                        vehicle_number,
                        vehicle_type
                    )
                )

                conn.commit()

            except psycopg2.errors.UniqueViolation:

                conn.rollback()
                cursor.close()
                conn.close()

                return redirect(
                    url_for("vehicles", error="duplicate")
                )

            cursor.close()
            conn.close()

        return redirect(
            url_for("vehicles", success="1")
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            vehicle_number,
            vehicle_type
        FROM vehicles
        WHERE user_id = %s
        ORDER BY id
        """,
        (user_id,)
    )

    vehicle_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "vehicles.html",
        vehicles=vehicle_list
    )


# =========================================================
# DELETE VEHICLE
# =========================================================

@app.route(
    "/vehicles/delete/<int:vehicle_id>",
    methods=["POST"]
)
def delete_vehicle(vehicle_id):

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check karo ki vehicle isi logged-in user ka hai ya nahi
    cursor.execute(
        """
        SELECT id
        FROM vehicles
        WHERE id = %s
        AND user_id = %s
        """,
        (vehicle_id, user_id)
    )

    vehicle = cursor.fetchone()

    if vehicle is None:
        cursor.close()
        conn.close()

        return f"""
        <script>
            alert("Vehicle not found!");
            window.location.href = "{url_for('vehicles')}";
        </script>
        """

    # Check karo ki vehicle ki koi booking hai ya nahi
    cursor.execute(
        """
        SELECT 1
        FROM bookings
        WHERE vehicle_id = %s
        LIMIT 1
        """,
        (vehicle_id,)
    )

    booking = cursor.fetchone()

    if booking:
        cursor.close()
        conn.close()

        return f"""
        <script>
            alert("This vehicle cannot be deleted because it has booking history.");
            window.location.href = "{url_for('vehicles')}";
        </script>
        """

    # Agar booking nahi hai, tab vehicle delete karo
    cursor.execute(
        """
        DELETE FROM vehicles
        WHERE id = %s
        AND user_id = %s
        """,
        (vehicle_id, user_id)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return f"""
    <script>
        alert("Vehicle deleted successfully!");
        window.location.href = "{url_for('vehicles')}";
    </script>
    """

# =========================================================
# PARKING SLOTS
# =========================================================

@app.route("/parking-slots", methods=["GET", "POST"])
def parking_slots():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        required_slots = [
            "A01", "A02", "A03", "A04", "A05",
            "B01", "B02", "B03", "B04", "B05"
        ]

        for slot_name in required_slots:

            cursor.execute("""
                INSERT INTO parking_slots
                (slot_number, status, vehicle_number)
                SELECT %s, 'Available', NULL
                WHERE NOT EXISTS (
                    SELECT 1 FROM parking_slots
                    WHERE slot_number = %s
                )
            """, (slot_name, slot_name))

        conn.commit()

        # POST: SELECT VEHICLE AND SLOT
        if request.method == "POST":

            slot_id = request.form.get("slot_id")
            vehicle_id = request.form.get("vehicle_id")

            if not slot_id or not vehicle_id:
                return redirect(url_for("parking_slots", error="missing"))

            cursor.execute("""
                SELECT id, slot_number, status
                FROM parking_slots
                WHERE id = %s
                FOR UPDATE
            """, (slot_id,))

            slot = cursor.fetchone()

            if slot is None or slot[2] != "Available":
                conn.rollback()
                return redirect(url_for("parking_slots", error="unavailable"))

            # CHECK VEHICLE BELONGS TO LOGGED-IN USER
            cursor.execute("""
                SELECT id, vehicle_number, vehicle_type
                FROM vehicles
                WHERE id = %s AND user_id = %s
            """, (vehicle_id, user_id))

            vehicle = cursor.fetchone()

            if vehicle is None:
                conn.rollback()
                return redirect(url_for("parking_slots", error="invalid_vehicle"))

            # CHECK PENDING BOOKING
            cursor.execute("""
                SELECT id
                FROM bookings
                WHERE user_id = %s
                AND status = 'Pending Payment'
                LIMIT 1
            """, (user_id,))

            existing_booking = cursor.fetchone()

            if existing_booking:
                conn.rollback()
                return redirect(url_for("slot_details"))

            # CREATE PENDING BOOKING
            cursor.execute("""
                INSERT INTO bookings
                (
                    user_id,
                    vehicle_id,
                    slot_id,
                    booking_date,
                    fee,
                    status
                )
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s)
            """, (
                user_id,
                vehicle_id,
                slot_id,
                20,
                "Pending Payment"
            ))

            # UPDATE PARKING SLOT STATUS
            cursor.execute("""
                UPDATE parking_slots
                SET status = 'Occupied',
                    vehicle_number = %s
                WHERE id = %s
            """, (vehicle[1], slot_id))

            conn.commit()

            # OPEN SLOT DETAILS
            return redirect(url_for("slot_details"))

        # GET PARKING SLOTS
        cursor.execute("""
            SELECT id, slot_number, status, vehicle_number
            FROM parking_slots
            WHERE slot_number IN (
                'A01', 'A02', 'A03', 'A04', 'A05',
                'B01', 'B02', 'B03', 'B04', 'B05'
            )
            ORDER BY slot_number
        """)

        slots = cursor.fetchall()

        # GET LOGGED-IN USER VEHICLES
        cursor.execute("""
            SELECT id, vehicle_number, vehicle_type
            FROM vehicles
            WHERE user_id = %s
            ORDER BY id
        """, (user_id,))

        vehicle_list = cursor.fetchall()

        return render_template(
            "parking_slots.html",
            slots=slots,
            vehicles=vehicle_list
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


# =========================================================
# SLOT DETAILS
# =========================================================

@app.route("/slot-details")
def slot_details():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                v.id,
                v.vehicle_number,
                v.vehicle_type,
                ps.id,
                ps.slot_number,
                ps.status

            FROM bookings b

            JOIN vehicles v
                ON b.vehicle_id = v.id

            JOIN parking_slots ps
                ON b.slot_id = ps.id

            WHERE b.user_id = %s
            AND b.status = 'Pending Payment'

            ORDER BY b.id DESC
            LIMIT 1
        """, (user_id,))

        booking = cursor.fetchone()

        if booking is None:
            return redirect(url_for("parking_slots"))

        vehicle = booking[0:3]
        slot = booking[3:6]

        return render_template(
            "slot_details.html",
            vehicle=vehicle,
            slot=slot
        )

    finally:
        cursor.close()
        conn.close()

# =========================================================
# BOOKING DETAILS
# =========================================================

@app.route("/booking-details")
def booking_details():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                b.id,
                v.id,
                v.vehicle_number,
                v.vehicle_type,
                ps.id,
                ps.slot_number,
                ps.status,
                b.fee,
                b.booking_date
            FROM bookings b
            JOIN vehicles v ON b.vehicle_id = v.id
            JOIN parking_slots ps ON b.slot_id = ps.id
            WHERE b.user_id = %s
            AND b.status = 'Pending Payment'
            ORDER BY b.id DESC
            LIMIT 1
        """, (user_id,))

        booking = cursor.fetchone()

        if booking is None:
            return redirect(url_for("my_bookings"))

        return render_template(
            "booking_details.html",
            booking=booking,
            vehicle=booking[1:4],
            slot=booking[4:7],
            fee=booking[7]
        )

    finally:
        cursor.close()
        conn.close()

# =========================================================
# PAYMENT
# =========================================================

@app.route("/payment")
def payment():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                b.id,
                v.id,
                v.vehicle_number,
                v.vehicle_type,
                ps.id,
                ps.slot_number,
                ps.status,
                b.fee
            FROM bookings b
            JOIN vehicles v ON b.vehicle_id = v.id
            JOIN parking_slots ps ON b.slot_id = ps.id
            WHERE b.user_id = %s
            AND b.status = 'Pending Payment'
            ORDER BY b.id DESC
            LIMIT 1
        """, (user_id,))

        booking = cursor.fetchone()

        if booking is None:
            return redirect(url_for("my_bookings"))

        return render_template(
            "payment.html",
            booking_id=booking[0],
            vehicle=booking[1:4],
            slot=booking[4:7],
            fee=booking[7]
        )

    finally:
        cursor.close()
        conn.close()

# =========================================================
# PAYMENT SUCCESSFUL
# =========================================================

@app.route("/payment-success", methods=["POST"])
def payment_success():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    booking_id = request.form.get("booking_id")

    payment_method = request.form.get(
        "payment_method",
        "UPI"
    )

    if not booking_id:
        return redirect(url_for("my_bookings"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                b.id,
                b.vehicle_id,
                b.slot_id,
                b.fee,
                b.status,
                v.vehicle_number,
                v.vehicle_type,
                ps.slot_number,
                ps.status
            FROM bookings b
            JOIN vehicles v ON b.vehicle_id = v.id
            JOIN parking_slots ps ON b.slot_id = ps.id
            WHERE b.id = %s
            AND b.user_id = %s
            FOR UPDATE OF b, ps
        """, (booking_id, user_id))

        booking = cursor.fetchone()

        if booking is None:
            return redirect(url_for("my_bookings"))

        if booking[4] == "Pending Payment":

            if booking[8] != "Occupied":
                conn.rollback()
                return redirect(url_for("parking_slots"))

            cursor.execute("""
                UPDATE bookings
                SET status = 'Booked'
                WHERE id = %s
                AND user_id = %s
            """, (booking_id, user_id))

            conn.commit()

        elif booking[4] != "Booked":

            conn.rollback()
            return redirect(url_for("my_bookings"))

        else:
            conn.commit()

        vehicle = (
            booking[1],
            booking[5],
            booking[6]
        )

        slot = (
            booking[2],
            booking[7],
            "Occupied"
        )

        return render_template(
            "payment_success.html",
            booking_id=booking[0],
            vehicle=vehicle,
            slot=slot,
            fee=booking[3],
            payment_method=payment_method
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

# =========================================================
# ENTRY / EXIT PAGE
# =========================================================

@app.route("/entry-exit")
def entry_exit():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                b.id,
                v.vehicle_number,
                v.vehicle_type,
                ps.slot_number,
                b.booking_date,
                b.entry_time,
                b.exit_time,
                b.fee,
                b.status

            FROM bookings b

            JOIN vehicles v
                ON b.vehicle_id = v.id

            JOIN parking_slots ps
                ON b.slot_id = ps.id

            WHERE b.user_id = %s

            ORDER BY b.id DESC

            LIMIT 1
            """,
            (user_id,)
        )

        booking = cursor.fetchone()

        return render_template(
            "entry_exit.html",
            booking=booking
        )

    finally:
        cursor.close()
        conn.close()



# =========================================================
# RECORD ENTRY
# =========================================================

@app.route(
    "/entry-exit/entry",
    methods=["POST"]
)
def record_entry():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    booking_id = request.form.get(
        "booking_id"
    )

    if not booking_id:

        return redirect(
            url_for(
                "entry_exit",
                error="no_booking"
            )
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                entry_time,
                status

            FROM bookings

            WHERE id = %s
            AND user_id = %s
            AND status IN ('Booked', 'Entered')
            """,
            (
                booking_id,
                user_id
            )
        )

        booking = cursor.fetchone()

        if booking is None:

            return redirect(
                url_for(
                    "entry_exit",
                    error="invalid"
                )
            )

        if booking[1] is not None:

            return redirect(
                url_for(
                    "entry_exit",
                    error="already_entry"
                )
            )

        cursor.execute(
            """
            UPDATE bookings

            SET
                entry_time = CURRENT_TIMESTAMP,
                status = 'Entered'

            WHERE id = %s
            AND user_id = %s
            """,
            (booking_id, user_id)
        )

        conn.commit()

        return redirect(
            url_for(
                "entry_exit",
                entry="1"
            )
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


# =========================================================
# RECORD EXIT + AUTOMATIC FEE
# =========================================================

@app.route("/entry-exit/exit", methods=["POST"])
def record_exit():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    booking_id = request.form.get("booking_id")

    if not booking_id:
        return redirect(
            url_for("entry_exit", error="no_booking")
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT id, slot_id, entry_time
            FROM bookings
            WHERE id = %s
            AND user_id = %s
            AND status = 'Entered'
        """, (booking_id, user_id))

        booking = cursor.fetchone()

        if not booking:
            return redirect(url_for("entry_exit"))

        booking_id, slot_id, entry_time = booking

        if entry_time is None:
            return redirect(url_for("entry_exit"))

        # Get exit time from PostgreSQL
        cursor.execute("SELECT CURRENT_TIMESTAMP")
        exit_time = cursor.fetchone()[0]

        # Calculate parking duration (timezone fix)
        if entry_time.tzinfo is None and exit_time.tzinfo is not None:
            exit_time = exit_time.replace(tzinfo=None)

        elif entry_time.tzinfo is not None and exit_time.tzinfo is None:
            exit_time = exit_time.replace(tzinfo=entry_time.tzinfo)

        duration = (exit_time - entry_time).total_seconds() / 3600

        # Calculate fee: ₹20 per hour
        charged_hours = max(1, math.ceil(duration))
        fee = charged_hours * 20

        # Update booking
        cursor.execute("""
            UPDATE bookings
            SET exit_time = %s,
                fee = %s,
                status = 'Completed'
            WHERE id = %s
            AND user_id = %s
        """, (exit_time, fee, booking_id, user_id))

        # Release parking slot
        cursor.execute("""
            UPDATE parking_slots
            SET status = 'Available',
                vehicle_number = NULL
            WHERE id = %s
        """, (slot_id,))

        conn.commit()

        return redirect(
            url_for("entry_exit", exit=1)
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()

# =========================================================
# MY BOOKINGS
# =========================================================

@app.route("/my-bookings")
def my_bookings():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                b.id,
                v.vehicle_number,
                v.vehicle_type,
                ps.slot_number,
                b.booking_date,
                b.entry_time,
                b.exit_time,
                b.fee,
                b.status

            FROM bookings b

            JOIN vehicles v
                ON b.vehicle_id = v.id

            JOIN parking_slots ps
                ON b.slot_id = ps.id

            WHERE b.user_id = %s

            ORDER BY b.id DESC
            """,
            (user_id,)
        )

        booking_list = cursor.fetchall()

        return render_template(
            "my_bookings.html",
            bookings=booking_list
        )

    finally:
        cursor.close()
        conn.close()



# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin_dashboard():

    conn = get_db_connection()
    cursor = conn.cursor()

    # TOTAL USERS
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        """
    )

    total_users = cursor.fetchone()[0]

    # TOTAL VEHICLES
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM vehicles
        """
    )

    total_vehicles = cursor.fetchone()[0]

    # TOTAL PARKING SLOTS
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM parking_slots
        """
    )

    total_slots = cursor.fetchone()[0]

    # AVAILABLE SLOTS
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM parking_slots
        WHERE status = 'Available'
        """
    )

    available_slots = cursor.fetchone()[0]

    # OCCUPIED SLOTS
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM parking_slots
        WHERE status = 'Occupied'
        """
    )

    occupied_slots = cursor.fetchone()[0]

    # TOTAL BOOKINGS
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM bookings
        """
    )

    total_bookings = cursor.fetchone()[0]

    # TOTAL REVENUE
    cursor.execute(
        """
        SELECT COALESCE(
            SUM(fee),
            0
        )

        FROM bookings

        WHERE status = 'Completed'
        """
    )

    total_revenue = cursor.fetchone()[0]

    # RECENT BOOKINGS
    cursor.execute(
        """
        SELECT
            b.id,
            v.vehicle_number,
            ps.slot_number,
            b.booking_date,
            b.status,
            b.fee

        FROM bookings b

        JOIN vehicles v
            ON b.vehicle_id = v.id

        JOIN parking_slots ps
            ON b.slot_id = ps.id

        ORDER BY b.id DESC

        LIMIT 10
        """
    )

    recent_bookings = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin_dashboard.html",

        total_users=total_users,

        total_vehicles=total_vehicles,

        total_slots=total_slots,

        available_slots=available_slots,

        occupied_slots=occupied_slots,

        total_bookings=total_bookings,

        total_revenue=total_revenue,

        recent_bookings=recent_bookings
    )


# =========================================================
# RUN FLASK
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )