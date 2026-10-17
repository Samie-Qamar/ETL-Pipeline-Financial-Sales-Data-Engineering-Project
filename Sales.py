import pandas as pd
import numpy as np
import oracledb
import os

try:
    connection = oracledb.connect(
        user="sys",
        password="1234",
        dsn="localhost:1521/xe",
        mode=oracledb.SYSDBA
    )

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM FinicialData")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
except Exception as a:
    print("Error:",a)
    
 


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
df = pd.read_excel(os.path.join(BASE_DIR, "Financial Sample.xlsx"))
print(df.columns)
#  Change Column Name

df.rename(columns={
    "Segment":"Sector",
    "Sale Price":"Sales",
    "Gross Sales":"GrossSales",
    "Discount Band":"Disc",
    "Month Name":"MM",
    "Month Number":"MonthNumber", 
    "Manufacturing Price":"ManufacturingPrice",
    "Units Sold":"UnitS"
},inplace=True)


# Merge Column Month Name & Year and Change Formt M-Y (MAR-25)
df["MM_YY"] = pd.to_datetime(df["MM"] + "-" + df['Year'].astype(str),format="%B-%Y").dt.strftime('%b-%y').str.upper()


# DROP MM - YEAR
df.drop(columns=["MM", "Year"], inplace=True)

#  Fill Na
df["Disc"]=df["Disc"].fillna("Low")

# Wirte and replace value
df.replace({"Country": {"United States of America": "USA"}}, inplace=True)

# Change Sales Data type and others
df["Date"] = pd.to_datetime(df["Date"]).dt.strftime('%Y-%m-%d')


# Reset Index
df.reset_index(drop=True,inplace=True)

print(df.loc[0])

#  INSERT ALL THE DATA IN FINICIALDATA TABLE AFETR CLEANING 

# =========================
# 6. FINAL INSERT (SAFE)
# ========================
# Duplicate check pandas se: table ka data DataFrame me la kar compare karo,
# sirf nayi rows insert hongi
DB_COLS = ["SEGMENT", "COUNTRY", "PRODUCT", "DISC", "UNITSOLD", "MANUFACTURINGPRICE", "SALES",
           "GROSSSALES", "DISCOUNTS", "PROFIT", "MONTHNUMBER", "MM_YY", "TRANSDATE"]
NUM_COLS = ["UNITSOLD", "MANUFACTURINGPRICE", "SALES", "GROSSSALES", "DISCOUNTS", "PROFIT", "MONTHNUMBER"]

# Excel data ko table ke column names me
new_df = pd.DataFrame({
    "SEGMENT": df["Sector"],
    "COUNTRY": df["Country"],
    "PRODUCT": df["Product"],
    "DISC": df["Disc"],
    "UNITSOLD": df["UnitS"],
    "MANUFACTURINGPRICE": df["ManufacturingPrice"],
    "SALES": df["Sales"],
    "GROSSSALES": df["GrossSales"],
    "DISCOUNTS": df["Discounts"],
    "PROFIT": df["Profit"],
    "MONTHNUMBER": df["MonthNumber"],
    "MM_YY": df["MM_YY"],
    "TRANSDATE": df["Date"]
})

# Excel ke andar wale duplicates hatao
total_rows = len(new_df)
new_df = new_df.drop_duplicates().reset_index(drop=True)

# Table me pehle se maujood data
cursor.execute("SELECT " + ", ".join(DB_COLS) + " FROM FinicialData")
existing_df = pd.DataFrame(cursor.fetchall(), columns=DB_COLS)

# Dono taraf same format bana kar har row ki ek key (DB number/date type ka farq khatam)
def make_key(data):
    k = data.copy()
    for c in NUM_COLS:
        k[c] = pd.to_numeric(k[c], errors="coerce").astype(float).round(2)
    k["TRANSDATE"] = pd.to_datetime(k["TRANSDATE"]).dt.strftime('%Y-%m-%d')
    k = k.astype(str).apply(lambda s: s.str.strip())
    return k.apply("|".join, axis=1)

if existing_df.empty:
    rows_to_insert = new_df
else:
    existing_keys = set(make_key(existing_df))
    rows_to_insert = new_df[~make_key(new_df).isin(existing_keys)]

for index, row in rows_to_insert.iterrows():

    cursor.execute("""
        INSERT INTO FinicialData (
            SEGMENT, COUNTRY, PRODUCT, DISC,
            UNITSOLD,MANUFACTURINGPRICE,SALES,GROSSSALES,DISCOUNTS,PROFIT,MONTHNUMBER,MM_YY,TRANSDATE
        )
        VALUES (
            :1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12,:13
        )
    """,
    tuple(row[c] for c in DB_COLS))

connection.commit()
print(f"Inserted: {len(rows_to_insert)} | Skipped (duplicate): {total_rows - len(rows_to_insert)}")


    