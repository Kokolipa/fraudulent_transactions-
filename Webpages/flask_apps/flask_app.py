# IMPORT DEPENDENCIES
# ----------------------------------------------------------------
# * Directory libraries
from pathlib import Path 

# * Analysis and manipulation libraries
import pandas as pd
import numpy as np 
import random
from datetime import datetime, timedelta

# * ML libraries
from sklearn.preprocessing import StandardScaler 
import pickle

# * Application libraries 
from flask import Flask, render_template, request, redirect, session, url_for
# from werkzeug.middleware.dispatcher import DispatcherMiddleware

# * Dashboard libraries
import plotly.express as px 
from dash import Dash, html, dcc
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
from dash_bootstrap_templates import load_figure_template
import dash_bootstrap_components as dbc
################################################################################


### FLASK APP ###
################################################################################
# * Instantiate the flask application
server = Flask(__name__)

# * Configure the '/' route
@server.route('/')
def index():
    return render_template('index.html')

# * Configure the '/transactions' route
@server.route('/transactions')
def transactions():
    return render_template('transactions.html')

# * Configure the '/upload' route
@server.route('/upload', methods=['POST'])
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
                
                
                ### USE THE PICKEL MODEL TO PREDICT FRAUDULENT TRANSACTIONS ###
                ################################################################
                # * Load the pickeled model
                pickled_model = pickle.load(open('model.pkl', 'rb'))
                
                # * predictions = Is_fraud
                is_fraud = pickled_model.predict(fraud_df)

                # * Create a pd.Series form is fraud 
                is_fraud = pd.Series(is_fraud, name="is_fraud")

                # * DataFrame with is_fraud (predictions)
                sample_df['is_fraud'] = is_fraud

                sample_df.to_csv("processed_data.csv", index=False)
                
                
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


### DASH APP ###
########################################################################
# * Loading the dataset
path = "/Users/galbeeir/Desktop/git/Project 4 - Fradulent Transactions/fraudulent_transactions/Webpages/flask_apps/processed_data.csv"

sample_df = pd.read_csv(path, parse_dates=["trans_date_trans_time", "dob"],infer_datetime_format=True)

columns_to_drop = ["cc_num", "unix_time", "zip"]
sample_df = sample_df.drop(columns_to_drop, axis=1)

# * Formatting category & merchant
sample_df['merchant'] = sample_df['merchant'].str.replace("fraud_", "")
sample_df['category'] = sample_df['category'].str.replace("_", " ")

# * Calculating the age of the person at the time of the transaction
sample_df['age'] = (sample_df['trans_date_trans_time'] - sample_df['dob']).apply(lambda x: x.days // 365)

# * Dropping the dob column
sample_df = sample_df.drop('dob', axis=1)

# * Modifying the gender column
sample_df['gender'] = sample_df['gender'].str.replace("M", "Male")
sample_df['gender'] = sample_df['gender'].str.replace("F", "Female")

# * Amount of transactions in the dataset
total_transactios = sample_df['trans_num'].count()
total_transactios_formatted = str(total_transactios)[:3] +"," +str(total_transactios)[3:]

# * The percentage of fraudulent transactions relative to non-fraudulent transactions
percentage_fraudulent = round((sample_df.query("is_fraud == 1")['is_fraud'].count()) / (sample_df.query("is_fraud == 0")['is_fraud'].count()), 3)
percentage_fraudulent_formatted = f"%{percentage_fraudulent}"

# * Importing external stylesheets
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"

# * Nameing the app, using the SLATE style theme, creating a route, and configuring the same server
app = Dash(__name__, external_stylesheets=[dbc.themes.SLATE, dbc_css], routes_pathname_prefix="/dashboard/", server=server)

# * Configuring the SLATE style theme on the figures
load_figure_template("SLATE")

# * Define filter labels
FILTER_LABELS = {
    1: 'Fraudulent',
    0: 'Non-Fraudulent',
    -1: 'All'
}


# * Determining the app_layout
app.layout = html.Div([
    html.Header([
        html.Meta(charSet='UTF-8'),
        html.Meta(name='viewport', content='width=device-width, initial-scale=1.0'),
        html.Meta(httpEquiv='X-UA-Compatible', content='ie=edge'),
        html.Title('Credit Card Fraud Analysis-dashboard'),
        # Define the CSS links
        html.Link(rel='preconnect', href='https://fonts.googleapis.com'),
        html.Link(rel='preconnect', href='https://fonts.gstatic.com', crossOrigin='true'),
        html.Link(rel='stylesheet', href='/static/styles.css'),  # Replace with the correct path
    ]),
    
    html.Nav(className='navbar navbar-dark bg-dark fixed-top', children=[
        html.Div(className='container-fluid', children=[
            html.A('Gal Beeri, Katharine Tamas, Mireille Walton', className='navbar-brand'),
            html.Button(type='button', style={'font-size': '14px'}, className='navbar-toggler', **{
                'data-bs-toggle': 'offcanvas',
                'data-bs-target': '#offcanvasDarkNavbar',
                'aria-controls': 'offcanvasDarkNavbar',
                'aria-label': 'Toggle navigation'
            }, children=[
                dcc.Link('Home', className='nav-link', href='/', target="_blank"),
            ]),
        ]),
    ]),

    # HERO BANNER
    html.Div(className='hero_banner', style={'height': '20px'}, children=[
        html.Img(src='/static/images/homepg_image.jpg', width='100%', height='350px'),
        html.Div(className='container-fluid', children=[
            html.Br(),
            html.Div(className='row', children=[
                html.Div(className='col-md-2'),
                html.Div(className='col-md-8', style={'height': '120px', 'margin-bottom': '300px'}, children=[
                    html.Br(),
                ]),
                html.Div(className='col-md-2'),
            ]),
        ]),
    ]),
                html.Div(children=[
                    html.Div(className='container-fluid', children=[
                        html.Div(className='row', style={'margin-top': '280px', 'backgroun-color':'rgba(15, 15, 15, 0.5)'}, children=[
                            html.Div(className='col-3 mx-auto my-5', children=[
                            ]),
                        ]),
                    ]),
                ]),


    html.Div(
        style={"width": "80%", "height": "80%", "margin-left": "8%", "margin-right": "8%"},
        children=[
        dbc.Row(html.H1(id="header"), style={"color":"white", "margin-top":"5px", "margin-bottom":"10px", "margin-left":"5px", "fontSize": "35px"}),
        dbc.Row(dbc.Card(dbc.RadioItems(
            id="dataFilter",
            options= [
                {'label': 'Fraudulent', 'value': 1},
                {'label': 'Non-Fraudulent', 'value': 0},
                {'label': 'All', 'value': -1}],
                value=0,
                inline=True
        ), style={"textAlign":"center"})),
    html.Br(),
    dbc.Row([
        dbc.Col(dbc.Card(f"Total Transactions: {total_transactios_formatted}"), style={"textAlign":"center",
                                                                                      "fontSize": "20px"},),
        dbc.Col(dbc.Card(f"Fraudulent: {percentage_fraudulent_formatted}"), style={"textAlign":"center",
                                                                                    "fontSize": "20px"}),
        ]),
    html.Br(),
    dbc.Row([
        dbc.Col(dbc.Card([
            dcc.Dropdown(
                id="features",
                options=sample_df.select_dtypes(include='object').columns[:-1],
                value= "category",
                className='dbc'
            ),
            dbc.RadioItems(
                id="asc-desc",
                options= [
                    {'label': 'Ascending', 'value': True},
                    {'label': 'Descending', 'value': False}],
                value=False,
                inline=True),
            dcc.Graph(id="hBarChart"),
            ]), width=4),
        dbc.Col(dbc.Card(dcc.Graph(id="histogram")), width=4),
        dbc.Col(dbc.Card(dcc.Graph(id="pieChart")), width=4)
        ]),
    html.Br(),
    dbc.Row(dbc.Card(dcc.Graph(id="scatterMapBox", style={"width": "100%"})))
    ]),
])

# * Configuring the Callback function
@app.callback(
    Output("header", "children"),
    Output("hBarChart", "figure"),
    Output("histogram", "figure"),
    Output("pieChart", "figure"),
    Output("scatterMapBox", "figure"),
    Input("dataFilter", "value"),
    Input("features", "value"),
    Input("asc-desc", "value")
)

# * Defining the dashboard returned function
def dashboard(filter_item, feature, sort_order):
    # * Prevent None values
    if filter_item is None:
        raise PreventUpdate()
    
    # * Match the filted label to the selected filter item
    filter_label = FILTER_LABELS.get(filter_item, 'Unknown Filter')
    
    # * Create a dynamic header
    header = f"{filter_label} Dashboard"

    # * Filter the datset based on the selected filter item
    if filter_item == 1:
        df = sample_df.query("is_fraud == 1")
    elif filter_item == 0:
        df = sample_df.query("is_fraud == 0")
    else:
        df = sample_df

    # * Plot the bar chart 
    bar = (
        px.bar(
        df.groupby(feature, as_index=False)["trans_num"].count().sort_values(by="trans_num", ascending=sort_order),
        x="trans_num",
        y=feature,
        color="trans_num",
        color_continuous_scale="Tealgrn",
        text_auto='.2s',
        title=f"Total Transactions by {feature} ({filter_label})"
        )
        .update_xaxes(
        title =f"Total Transactions")
        .update_layout(
        title = {
            'x': 0.12,
            'y': .85
        },
        coloraxis_showscale=False,
        plot_bgcolor='rgba(15, 15, 15, 0)',
        paper_bgcolor='rgba(15, 15, 15, 0.5)'
        )
    )

    # * Plot the histogram
    histogram = (
    px.histogram(
        df.groupby("age", as_index=False)['trans_num'].count(),
        x="age",
        y="trans_num",
        title=f"Destribution of Transactions by Age ({filter_label})"
        )
        .update_traces(marker_color='rgba(49, 252, 3, 0.6)', marker_line_color='#2ad104',
                       marker_line_width=1.5,
                       opacity=0.6)
        .update_layout(
        title = {
            "x": 0.075,
            "y": .85
        },
        plot_bgcolor='rgba(15, 15, 15, 0)',
        paper_bgcolor='rgba(15, 15, 15, 0.5)')
    )

    # * Plot the pie chart
    pie = (
        px.pie(
        df.groupby("gender", as_index=False)["trans_num"].count(),
        values="trans_num",
        names="gender",
        hole=0.46,
        color_discrete_sequence=['rgba(252, 3, 3, 0.7)', 'rgba(49, 252, 3, 0.6)'])
        .update_layout(
        title_text=f"Transactions Breakdown ({filter_label})",
        annotations=[dict(text='Gender %',
                     x=0.5,
                     y=0.5,
                     font_size=16,
                     showarrow=False)],
        title = {
            "x": 0.48
        },
        plot_bgcolor='rgba(15, 15, 15, 0)',
        paper_bgcolor='rgba(15, 15, 15, 0.5)')
    )

    # * Plot the scatter_mapbox
    map_scatter = (
        px.scatter_mapbox(
        df.groupby(["city", "lat", "long"])["trans_num"].count().reset_index(),
        lat="lat",
        lon="long",
        size="trans_num",
        color="trans_num",
        color_continuous_scale=px.colors.sequential.Jet,
        zoom=4.5,
        center=dict(
        lat=37.9931,
        lon=-100.9893
        ),
        mapbox_style="carto-darkmatter",
        title=f"Destribution of Transactions ({filter_label})",
        hover_data=["city"],
        hover_name="city",
        )
        .update_layout(
        title={
            "x":0.038,
            "y":.85
        },
        coloraxis_colorbar = dict(
        thicknessmode="pixels",
        thickness=15,
        title="Count"
        ),
        plot_bgcolor='rgba(15, 15, 15, 0)',
        paper_bgcolor='rgba(15, 15, 15, 0.5)')
    )


    return header, bar, histogram, pie, map_scatter


if __name__ == '__main__':
    server.run(debug=True)