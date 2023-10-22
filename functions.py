import pymysql

connection = pymysql.connect(
    host='localhost',
    user='root',
    password='',
    db='PhoneBook'
)


def is_username_taken(username):
    with connection.cursor() as cursor:
        sql = "SELECT username FROM users;"
        cursor.execute(sql)
        results = cursor.fetchall()

    for name in results:
        if username == name[0]:
            return True
    return False

