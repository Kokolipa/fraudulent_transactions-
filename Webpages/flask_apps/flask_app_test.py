# IMPORT DEPENDENCIES
# ----------------------------------------------------------------
from flask import Flask, render_template, request
import pandas as pd
import numpy as np 
from pathlib import Path 
from sklearn.preprocessing import StandardScaler 
import random
from datetime import datetime, timedelta
import pickle

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transactions')
def transactions():
    return render_template('transactions.html')

@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            try:
                # Save the uploaded file
                file.save('uploaded_file.csv')

                # Read the CSV file using pandas
                sample_df = pd.read_csv('uploaded_file.csv')

                ### SCALING THE DATASET  ###
                ################################################################
                # Create a copy of the sample dataframe -
                fraud_df = sample_df.copy()
                
                # Drop the cc_num and trans_num columns as credit numbers are randomly generated by the banks and 
                # have no link to whether fraud will be committed
                fraud_df.drop(['cc_num','trans_num'], axis=1, inplace=True)

                # Convert 'trans_date_trans_time' from object to date time format
                fraud_df['trans_date_trans_time'] = pd.to_datetime(fraud_df['trans_date_trans_time'], format='%Y-%m-%d %H:%M:%S')
                
                # Sort transaction date and time in ascending order
                fraud_df = fraud_df.sort_values(by='trans_date_trans_time', ascending=True)

                # Number of rows to generate based on rows in sample file uploaded
                num_rows = len(fraud_df)

                # Initialize 'is_fraud' column with 0
                fraud_df['is_fraud'] = 0

                # Set 'is_fraud' to 1 for the first transaction
                fraud_df.loc[0, 'is_fraud'] = 1

                # Set 'is_fraud' to 1 for transactions every 7 days
                for i in range(1, len(fraud_df)):
                    time_difference = fraud_df['trans_date_trans_time'].iloc[i] - fraud_df['trans_date_trans_time'].iloc[i - 1]
                    if time_difference >= timedelta(days=7):
                        fraud_df.loc[i, 'is_fraud'] = 1

                fraud_df.reset_index(drop=True, inplace=True)

                # Convert the 'trans_date_trans_time' column to datetime objects
                fraud_df['trans_date_trans_time'] = pd.to_datetime(fraud_df['trans_date_trans_time'], format='%Y-%m-%d %H:%M:%S')

                # Convert the 'trans_date_trans_time' column to Unix timestamps
                fraud_df['trans_date_trans_time'] = (fraud_df['trans_date_trans_time'] - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')

                # Convert the 'dob' column to datetime objects
                fraud_df['dob'] = pd.to_datetime(fraud_df['dob'], format='%Y-%m-%d')

                # Convert the 'dob' column to Unix timestamps
                fraud_df['dob'] = (fraud_df['dob'] - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')

                # Scale the numeric columns.
                # Scaling the data is necessary to ensure that features with different units or magnitudes have an equal 
                # influence on machine learning algorithms and to enable efficient convergence.

                # Define the columns you want to scale (assuming they are all numeric)
                columns_to_scale = ['trans_date_trans_time', 'amt','zip','lat','long','city_pop','dob','unix_time','merch_lat','merch_long']

                # Initialize the StandardScaler
                scaler = StandardScaler()

                # Fit the scaler on your data and transform the specified columns
                fraud_df[columns_to_scale] = scaler.fit_transform(fraud_df[columns_to_scale])

                # Implement target encoding for each feature and the 'is_fraud' target variable
                # Calculate the mean 'is_fraud' for each 'merchant'
                target_mean = fraud_df.groupby('merchant')['is_fraud'].mean()
                # Replace merchant column with the target encoding
                fraud_df['merchant'] = fraud_df['merchant'].map(target_mean)


                # Calculate the mean 'is_fraud' for each 'job'
                target_mean = fraud_df.groupby('category')['is_fraud'].mean()
                # Replace category column with the target encoding
                fraud_df['category'] = fraud_df['category'].map(target_mean)


                # Calculate the mean 'is_fraud' for each 'first'
                target_mean = fraud_df.groupby('first')['is_fraud'].mean()
                # Replace first column with the target encoding
                fraud_df['first'] = fraud_df['first'].map(target_mean)


                # Calculate the mean 'is_fraud' for each 'last'
                target_mean = fraud_df.groupby('last')['is_fraud'].mean()
                # Replace last column with the target encoding
                fraud_df['last'] = fraud_df['last'].map(target_mean)


                # Calculate the mean 'is_fraud' for each 'street'
                target_mean = fraud_df.groupby('street')['is_fraud'].mean()
                # Replace street column with the target encoding
                fraud_df['street'] = fraud_df['street'].map(target_mean)


                # Calculate the mean 'is_fraud' for each 'city'
                target_mean = fraud_df.groupby('city')['is_fraud'].mean()
                # Replace city column with the target encoding
                fraud_df['city'] = fraud_df['city'].map(target_mean)


                # Calculate the mean 'is_fraud' for each 'state'
                target_mean = fraud_df.groupby('state')['is_fraud'].mean()
                # Replace state column with the target encoding
                fraud_df['state'] = fraud_df['state'].map(target_mean)


                # Calculate the mean 'is_fraud' for each 'job'
                target_mean = fraud_df.groupby('job')['is_fraud'].mean()
                # Replace job column with the target encoding
                fraud_df['job'] = fraud_df['job'].map(target_mean)


                # Replace "M" with 1 and "F" with 0 in the "gender" column
                fraud_df['gender'] = fraud_df['gender'].replace({'M': 1, 'F': 0})

                # Drop is_fraud column
                fraud_df.drop(['is_fraud'], axis=1, inplace=True)
                
                
                ### PICKELED THE DATA ###
                ################################################################
                # * Load the pickeled model
                pickled_model = pickle.load(open('model.pkl', 'rb'))
                
                # * predictions = Is_fraud
                is_fraud = pickled_model.predict(fraud_df)

                # * Create a pd.Series form is fraud 
                is_fraud = pd.Series(is_fraud, name="is_fraud")

                # * DataFrame with is_fraud (predictions)
                sample_df['is_fraud'] = is_fraud
                
                
                ### GET LIST OF TRANSACTIONS TO VIEW ###
                ################################################################
                # Extract the columns you need (change 'desired_column' to your desired column name)
                selected_column = sample_df[['trans_date_trans_time', 'cc_num', 'merchant','category', 'amt', 'trans_num', 'is_fraud']]

                def format_fraud_column(val):
                    if val == 0:
                        return '<span style="font-size: 25px; text-align: right; color: green;">&#x2713</span>'  #insert green tick if not fraud
                    elif val == 1:
                        return '<span style="font-size: 25px; text-align: right; color: orange;">&#10071</span>'  #insert orange exclamation if potentially fraudulent
                    else:
                        return val

                # Sort the 'is_fraud' column in descending order
                selected_column = selected_column.sort_values(by='is_fraud', ascending=False)

                # Apply the formatting function to the 'is_fraud' column
                selected_column['is_fraud'] = selected_column['is_fraud'].apply(format_fraud_column)

                # Convert the selected data to an HTML table
                table_html = selected_column.to_html(index=False, escape=False)

                # Return the HTML content as the response
                return render_template('/transactions.html', table_data=table_html)
            
            except Exception as e:
                return f"An error occurred: {str(e)}"

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(debug=True)