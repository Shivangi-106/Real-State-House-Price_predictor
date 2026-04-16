'''
import streamlit as st
import pandas as pd
import numpy as np
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from joblib import dump, load
import mysql.connector

# ------------------ DB CONFIG ------------------
DB_CONFIG = {
    'host': 'localhost',         # 🔁 Change if needed
    'user': 'root',              # 🔁 Change to your MySQL username
    'password': '143143', # 🔁 Change to your MySQL password
    'database': 'house_price_db'
}

MODEL_FILE = "model.joblib"

COLUMNS = ['CRIM', 'ZN', 'INDUS', 'CHAS', 'NOX', 'RM', 'AGE',
           'DIS', 'RAD', 'TAX', 'PTRATIO', 'B', 'LSTAT']

# ------------------ DB FUNCTIONS ------------------
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def fetch_data(table):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()
    return df

def insert_input_to_db(data_dict, table='data_copy'):
    conn = get_connection()
    cursor = conn.cursor()

    cols = ', '.join(data_dict.keys())
    vals = ', '.join(['%s'] * len(data_dict))
    sql = f"INSERT INTO {table} ({cols}) VALUES ({vals})"

    cursor.execute(sql, tuple(data_dict.values()))
    conn.commit()
    cursor.close()
    conn.close()

def move_data_to_main():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO housing_data (CRIM, ZN, INDUS, CHAS, NOX, RM, AGE, DIS, RAD, TAX, PTRATIO, B, LSTAT, MEDV) SELECT CRIM, ZN, INDUS, CHAS, NOX, RM, AGE, DIS, RAD, TAX, PTRATIO, B, LSTAT, MEDV FROM data_copy")
    cursor.execute("DELETE FROM data_copy")
    conn.commit()
    cursor.close()
    conn.close()

# ------------------ MODEL ------------------
def train_and_save_model(df):
    df_clean = df.dropna(subset=['MEDV'])
    X = df_clean[COLUMNS]
    y = df_clean['MEDV']
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('model', RandomForestRegressor())
    ])
    pipeline.fit(X, y)
    dump(pipeline, MODEL_FILE)
    return pipeline

# ------------------ LOAD MODEL ------------------
try:
    model = load(MODEL_FILE)
except:
    df_init = fetch_data('housing_data')
    model = train_and_save_model(df_init)

# ------------------ UI ------------------
st.title("🏠 Real Estate Price Prediction")

st.markdown("""
Enter the property details below. Please follow the format guidelines:

- **CRIM**: Crime in % (e.g., `2` for 2%)
- **ZN**: Residential zone in % (e.g., `25`)
- **INDUS**: Industry area in % (e.g., `15`)
- **CHAS**: 0 = No river bound, 1 = River bound
- **NOX**: Nitric oxide concentration in % (e.g., `0.5`)
- **RM**: Number of rooms (e.g., `3`, `6.5`)
- **AGE**: Age of house (e.g., `50`)
- **DIS**: Distance to jobs in km (e.g., `4.2`)
- **RAD**: Highway access in km (e.g., `3`)
- **TAX**: Tax in % per $1000 (e.g., `18`)
- **PTRATIO**: Pupil-teacher ratio (e.g., `15.5`)
- **B**: Black population index (as-is)
- **LSTAT**: Lower status population % (e.g., `5.3`)
""")

user_input = {}
empty_count = 0

for col in COLUMNS:
    val = st.text_input(f"{col}:", key=col)
    if val.strip() == '':
        empty_count += 1
    user_input[col] = val.strip()

if st.button("Predict"):
    if empty_count > 2:
        st.error("❌ Please fill at least 11 out of 13 fields.")
    else:
        try:
            processed = {}
            for col in COLUMNS:
                val = user_input[col]
                if val == '':
                    processed[col] = np.nan
                else:
                    num = float(val)
                    if col in ['CRIM', 'ZN', 'INDUS', 'NOX', 'LSTAT', 'TAX']:
                        processed[col] = num / 100
                    elif col == 'CHAS':
                        processed[col] = int(num)
                    else:
                        processed[col] = num

            input_df = pd.DataFrame([processed])
            filled_input = input_df.fillna(fetch_data('housing_data')[COLUMNS].mean())
            prediction = model.predict(filled_input)[0]
            st.success(f"💵 Predicted house price: ${prediction * 1000:,.0f}")

            input_df['MEDV'] = round(prediction, 1)
            insert_input_to_db(input_df.iloc[0].to_dict(), table='data_copy')

            # Retrain after every 10 entries
            copy_data = fetch_data('data_copy')
            if len(copy_data) >= 10:
                retrained_model = train_and_save_model(copy_data)
                model = retrained_model
                move_data_to_main()  # clear data_copy and move to housing_data

        except Exception as e:
            st.error(f"⚠️ Error: {e}")
'''


import streamlit as st
import pandas as pd
import numpy as np
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from joblib import dump, load
import mysql.connector
from mysql.connector import Error

# ------------------ DB CONFIG ------------------
DB_CONFIG = {
    'host': '127.0.0.1',      # Use 127.0.0.1 for Windows
    'user': 'root',           # Change to your MySQL username
    'password': '143143',     # Change to your MySQL password
    'database': 'house_price_db'
}

MODEL_FILE = "model.joblib"

COLUMNS = ['CRIM', 'ZN', 'INDUS', 'CHAS', 'NOX', 'RM', 'AGE',
           'DIS', 'RAD', 'TAX', 'PTRATIO', 'B', 'LSTAT']

# ------------------ DB FUNCTIONS ------------------
def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        st.error(f"❌ MySQL connection failed: {e}")
        return None

def fetch_data(table):
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()  # Return empty dataframe if connection fails
    try:
        df = pd.read_sql(f"SELECT * FROM {table}", conn)
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def insert_input_to_db(data_dict, table='data_copy'):
    conn = get_connection()
    if conn is None:
        return
    try:
        cursor = conn.cursor()
        cols = ', '.join(data_dict.keys())
        vals = ', '.join(['%s'] * len(data_dict))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({vals})"
        cursor.execute(sql, tuple(data_dict.values()))
        conn.commit()
    except Exception as e:
        st.error(f"Error inserting data: {e}")
    finally:
        cursor.close()
        conn.close()

def move_data_to_main():
    conn = get_connection()
    if conn is None:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO housing_data (CRIM, ZN, INDUS, CHAS, NOX, RM, AGE, DIS, RAD, TAX, PTRATIO, B, LSTAT, MEDV)
            SELECT CRIM, ZN, INDUS, CHAS, NOX, RM, AGE, DIS, RAD, TAX, PTRATIO, B, LSTAT, MEDV FROM data_copy
        """)
        cursor.execute("DELETE FROM data_copy")
        conn.commit()
    except Exception as e:
        st.error(f"Error moving data: {e}")
    finally:
        cursor.close()
        conn.close()

# ------------------ MODEL FUNCTIONS ------------------
def train_and_save_model(df):
    df_clean = df.dropna(subset=['MEDV'])
    if df_clean.empty:
        st.error("No data available to train the model.")
        return None

    X = df_clean[COLUMNS]
    y = df_clean['MEDV']
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('model', RandomForestRegressor())
    ])
    pipeline.fit(X, y)
    dump(pipeline, MODEL_FILE)
    return pipeline

def load_model():
    if os.path.exists(MODEL_FILE):
        try:
            return load(MODEL_FILE)
        except Exception as e:
            st.warning(f"Error loading saved model: {e}")
    # If model doesn't exist or fails, train from DB
    df_init = fetch_data('housing_data')
    return train_and_save_model(df_init)

# ------------------ STREAMLIT UI ------------------
st.title("🏠 Real Estate Price Prediction")

st.markdown("""
Enter the property details below. Fill at least 11 out of 13 fields:

- **CRIM**: Crime rate (e.g., 2)  
- **ZN**: Residential zone percentage (e.g., 25)  
- **INDUS**: Non-retail business area percentage (e.g., 15)  
- **CHAS**: 0 = No river, 1 = River bound  
- **NOX**: Nitric oxide concentration (e.g., 0.5)  
- **RM**: Average number of rooms (e.g., 6.5)  
- **AGE**: Proportion of owner-occupied units built before 1940 (e.g., 50)  
- **DIS**: Distance to employment centers (e.g., 4.2)  
- **RAD**: Accessibility to highways (e.g., 3)  
- **TAX**: Property tax rate per $10,000 (e.g., 18)  
- **PTRATIO**: Pupil-teacher ratio (e.g., 15.5)  
- **B**: Proportion of Black residents (as-is)  
- **LSTAT**: % lower status population (e.g., 5.3)
""")

# Collect user input
user_input = {}
empty_count = 0
for col in COLUMNS:
    val = st.text_input(f"{col}:", key=col)
    if val.strip() == '':
        empty_count += 1
    user_input[col] = val.strip()

# Load or train model
model = load_model()

# Prediction button
if st.button("Predict"):
    if empty_count > 2:
        st.error("❌ Please fill at least 11 out of 13 fields.")
    elif model is None:
        st.error("Model not available. Check your database and model file.")
    else:
        try:
            processed = {}
            for col in COLUMNS:
                val = user_input[col]
                if val == '':
                    processed[col] = np.nan
                else:
                    num = float(val)
                    processed[col] = num

            input_df = pd.DataFrame([processed])
            # Fill missing values with mean from DB
            db_data = fetch_data('housing_data')
            if not db_data.empty:
                filled_input = input_df.fillna(db_data[COLUMNS].mean())
            else:
                filled_input = input_df.fillna(0)

            prediction = model.predict(filled_input)[0]
            st.success(f"💵 Predicted house price: ${prediction * 1000:,.0f}")

            # Insert input + prediction into data_copy
            input_df['MEDV'] = round(prediction, 1)
            insert_input_to_db(input_df.iloc[0].to_dict(), table='data_copy')

            # Retrain model every 10 entries
            copy_data = fetch_data('data_copy')
            if len(copy_data) >= 10:
                retrained_model = train_and_save_model(copy_data)
                if retrained_model is not None:
                    model = retrained_model
                    move_data_to_main()  # move data_copy → housing_data

        except Exception as e:
            st.error(f"⚠️ Prediction error: {e}")
