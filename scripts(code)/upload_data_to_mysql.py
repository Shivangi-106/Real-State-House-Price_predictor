import pandas as pd
import mysql.connector

# Load your local data.csv
df = pd.read_csv('data.csv')

# Connect to MySQL
conn = mysql.connector.connect(
    host='localhost',         # or your MySQL host
    user='root',              # your MySQL username
    password='143143', # your MySQL password
    database='house_price_db' # your database name
)

cursor = conn.cursor()

# Insert each row into the housing_data table
for _, row in df.iterrows():
    sql = """
        INSERT INTO housing_data
        (CRIM, ZN, INDUS, CHAS, NOX, RM, AGE, DIS,
         RAD, TAX, PTRATIO, B, LSTAT, MEDV)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        float(row['CRIM']),
        float(row['ZN']),
        float(row['INDUS']),
        int(row['CHAS']),
        float(row['NOX']),
        float(row['RM']),
        float(row['AGE']),
        float(row['DIS']),
        int(row['RAD']),
        float(row['TAX']),
        float(row['PTRATIO']),
        float(row['B']),
        float(row['LSTAT']),
        float(row['MEDV'])
    )
    cursor.execute(sql, values)

conn.commit()
conn.close()

print("Data from data.csv has been successfully imported into housing_data table in MySQL.")
