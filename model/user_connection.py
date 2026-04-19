import psycopg as pg

class UserConecction():
    conn = None

    def __init__(self): ##constructor
        try:
            self.conn = pg.connect("dbname=Servi_meca user=postgres password=fabicra4004M host=localhost port=5432");
        except pg.OperationalError as err:
            print(err)
            self.conn.close();
    
    def write(self, data):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "users" (name, email, password, phone, location) 
                VALUES (
                        %(name)s, 
                        %(email)s, 
                        %(password)s, 
                        %(phone)s, 
                        %(location)s)     
            """,data)
        self.conn.commit()

    def read_all(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM "users"
            """)
            return cur.fetchall()
        
    def read_one(self, user_id):
        with self.conn.cursor() as cur:
            data = cur.execute("""
                SELECT * FROM "users" WHERE id = %s
            """, (user_id,))
            return data.fetchone()
    
    def delete(self, user_id):
        with self.conn.cursor() as cur:
            cur.execute("""
                DELETE FROM "users" WHERE id = %s
            """, (user_id,))
        self.conn.commit()

    def update(self, data):
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE "users" SET 
                        name = %(name)s, 
                        email = %(email)s, 
                        password = %(password)s, 
                        phone = %(phone)s, 
                        location = %(location)s 
                        WHERE id = %(id)s
            """,data)
        self.conn.commit()

    def __def__(self): ##destructor
        self.conn.close()