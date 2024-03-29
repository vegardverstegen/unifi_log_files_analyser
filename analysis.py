import sys
import pandas
import matplotlib.pyplot as plt
from fpdf import FPDF
import re
from datetime import datetime
import requests
from shapely.geometry import Point
import geopandas
import os
import hashlib


#Function that imports a csv file and returns a pandas dataframe
def import_csv(path):
    data = pandas.read_csv(path, sep=',', quotechar='|')
    return data

#Function that extracts the file type from the path
def extract_file_type(path):
    file_type = path.split('/')[-1]
    file_type = file_type.split('\\')[-1]
    file_type = file_type.split('_')[0]
    return file_type

def string_to_list(string):
    lst = string.strip('[]').replace('\'', '').split(', ')
    return lst

def check_if_known_device(df, ip:str='', mac:str='', name:str='') -> bool:
    if ip in df['IP Address'].values: return True
    if mac in df['MAC Address'].values: return True
    if name in df['Device Name'].values: return True
    return False

def get_known_device(df, ip:str='', mac:str='', name:str='') -> dict:
    if ip in df['IP Address'].values:
        row = df.loc[df['IP Address'] == ip]
    if mac in df['MAC Address'].values:
        row = df.loc[df['MAC Address'] == mac]
    if name in df['Device Name'].values:
        row = df.loc[df['Device Name'] == name]
    return {'name': row['Device Name'].values[0], 'ip': row['IP Address'].values[0], 'mac': row['MAC Address'].values[0]}

def get_known_device_list(known_df, df):
    known_device_list = []
    for _, row in df.iterrows():
        if check_if_known_device(known_df, ip=row['IP Address']):
            known_device_list.append(get_known_device(known_df, ip=row['IP Address']))
    return known_device_list

#Takes two datetimes in the format 'dd-mm HH:MM:SS' and returns the times in the order 'earliest time', 'latest time'
def compare_times(time1: str, time2: str) -> tuple:
    d1, m1, H1, M1, S1 = re.split(' |:|-', time1)
    d2, m2, H2, M2, S2 = re.split(' |:|-', time2)
    #Add buffer for new year
    if m1 >= '10' and m2 <= '03': return time1, time2
    if m1 <= '03' and m2 >= '10': return time2, time1
    #Compare times
    if d1 < d2: return time1, time2
    elif d1 > d2: return time2, time1
    if m1 < m2: return time1, time2
    elif m1 > m2: return time2, time1
    if H1 < H2: return time1, time2
    elif H1 > H2: return time2, time1
    if M1 < M2: return time1, time2
    elif M1 > M2: return time2, time1
    if S1 < S2: return time1, time2
    elif S1 > S2: return time2, time1
    #Times are equal
    return time1, time2

def find_time_span(lst: list) -> tuple:
    earliest = latest = lst[0]
    for time in lst:
        earliest, tmp = compare_times(earliest, time)
        tmp, latest = compare_times(time, latest)

    return earliest, latest

def detect_anomalies(df):
    anomalies = []
    #List of strings to look for in the log file
    detection_strings = [
        'Bad password attempt',
        'Passwrord auth succeeded'
    ]
    for _, row in df.iterrows():
        #Chekcs each rows message for the detection strings using regex
        for string in detection_strings:
            if re.search(string, row['Message']):
                anomalies.append(row)
    return anomalies

#Function that makes a bar chart from a pandas dataframe with matplotlib
def make_bar_chart(dataframe, x_axis, y_axis, title, x_label, y_label, save_path):
    plt.cla()
    #List of colors to use for the bars. Good colors for presenting scientific data
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    plt.bar(dataframe[x_axis], dataframe[y_axis], color=colors, width=0.8, linewidth=0.5)
    #Make x_axis labels smaller
    plt.xticks(rotation=30, size=8, ha='right')
    #Adding title and labels
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    #Adjust sizing
    plt.tight_layout()
    plt.savefig(save_path)

def common_ip(dataframe):
    ip_counter = pandas.DataFrame(columns=['IP Address', 'Occurrences', 'First Time', 'Last Time', 'Time Delta', 'Requests per Hour'])
    #Loop through IP addresses occurences, and times in the dataframe
    for _, row in dataframe.iterrows():
        IPs = string_to_list(row['IP Address'])
        occurrences = row['Occurrences']
        times = string_to_list(row['Timestamp'])
        first_time, last_time = find_time_span(times)
        #Loop through IP addresses on each row
        for i in IPs:
            #Chek if IP exists
            if i:
                #Check if IP address is already in the dataframe row
                if i in ip_counter['IP Address'].values:
                    #If it is, add the occurrences, first_time and last_time to the existing row
                    ip_counter.loc[ip_counter['IP Address'] == i, 'Occurrences'] += occurrences
                    #Extract and compare times, and update the dataframe
                    time = str(ip_counter.loc[ip_counter['IP Address'] == i, 'First Time'].values).strip('[]').replace('\'', '')
                    ip_counter.loc[ip_counter['IP Address'] == i, 'First Time'] = compare_times(first_time, time)[0]
                    time = str(ip_counter.loc[ip_counter['IP Address'] == i, 'Last Time'].values).strip('[]').replace('\'', '')
                    ip_counter.loc[ip_counter['IP Address'] == i, 'Last Time'] = compare_times(last_time, time)[1]
                    
                else:
                    #If it isn't, add a new row
                    ip_counter = pandas.concat([ip_counter, pandas.DataFrame([[i, occurrences, first_time, last_time]], columns=['IP Address', 'Occurrences', 'First Time', 'Last Time'])], ignore_index=True)
                    
                
    #Add a column with an average of requests per hour
    for index, row in ip_counter.iterrows():
        timedelta = (datetime.strptime(row['Last Time'], '%d-%m %H:%M:%S')) - (datetime.strptime(row['First Time'], '%d-%m %H:%M:%S'))
        timedelta = timedelta.total_seconds() / 3600
        if timedelta:
            row['Requests per Hour'] = int(row['Occurrences'] / timedelta)
        timedelta = round(timedelta, 2)
        row['Time Delta'] = timedelta

    return ip_counter

#Function that visualises the most common IP addresses and retursn a list of known devices in the chart
def most_common_ip_visual(ip_counter, device_info, IPs_in_chart, output_folder):
    #Visualise the most common IP addresses by total requests
    ip_counter_total = ip_counter.sort_values(by=['Occurrences'], ascending=False)
    make_bar_chart(ip_counter_total.head(IPs_in_chart), 'IP Address', 'Occurrences', f'Top {IPs_in_chart} - Total Requests', 'IP address', 'Occurrences', f'{output_folder}\\visualisations\\most_common_ip.png')
    #Make list of known devices in chart
    known_total = get_known_device_list(device_info, ip_counter_total.head(IPs_in_chart)) #Get known devices in chart for total requests

    #Visualise the most common IP addresses by requests per hour
    ip_counter_perHour = ip_counter.sort_values(by=['Requests per Hour'], ascending=False)
    make_bar_chart(ip_counter_perHour.head(IPs_in_chart), 'IP Address', 'Requests per Hour', f'Top {IPs_in_chart} - Requests per hour', 'IP address', 'Requests per hour', f'{output_folder}\\visualisations\\most_common_ip_perHour.png')
    #Make list of known devices in chart
    known_perHour = get_known_device_list(device_info, ip_counter_perHour.head(IPs_in_chart)) #Get known devices in chart for requests per hour

    return known_total, known_perHour

#Function that uses an API to get the coordinates of the IP addresses
def get_coordinates(vpn, apiKey):
    locations = []
    for _, row in vpn.iterrows():
        ips = row['IP Address']
        #Only search for IP addresses that are initiating a VPN connection
        if 'is initiating a Main Mode IKE_SA' in row['Message'] or 'establishing CHILD_SA peer' in row['Message']:
            for ip in string_to_list(ips):
                response = requests.get(f'https://api.ipgeolocation.io/ipgeo?apiKey={apiKey}&ip={ip}').json()
                locations.append(response)
    return pandas.DataFrame.from_dict(locations)

def generate_vpn_map(locations, output_folder):
    coordinates = [Point(xy) for xy in zip(locations['longitude'], locations['latitude'])]
    gdf = geopandas.GeoDataFrame(locations, geometry=coordinates)
    world_map = geopandas.read_file(geopandas.datasets.get_path('naturalearth_lowres'))
    fig = gdf.plot(ax=world_map.plot(figsize=(10, 6)), marker='o', color='red', markersize=15).get_figure()
    fig.savefig(f'{output_folder}\\visualisations\\vpn_map.png')
            
def reduce_coordinates(df):
    df = df[['ip', 'country_name', 'city', 'isp', 'organization']]
    df = df.rename(columns={'ip': 'IP Address', 'country_name': 'Country', 'city': 'City', 'isp': 'ISP', 'organization': 'Organization'})
    return df

#Function that creates a final report in pdf format
def create_pdf(df, device_info, ip_counter, known_total_max, known_perHour_max, anomalies, VPNcoordinates, filetype, output_folder):
    #Interpret filetype
    filetypes = {'usg': 'Unifi Security Gateway', 'usw': 'Unifi Switch'}
    filetype = filetypes[filetype]
    #FPDF setup
    class PDF(FPDF):
        def header(self):
            #Logo
            #self.image('logo.png', 10, 8, 33)
            #Title
            self.set_font('Helvetica', '', 8)
            self.cell(0, 10, f'Analysis of {filetype}', new_x='LMARGIN', new_y='NEXT', align='C')
            #Line break
            self.ln(5)
    
        def footer(self):
            #Position at 1.5 cm from bottom
            self.set_y(-15)
            #Font
            self.set_font('Helvetica', 'I', 8)
            #Page number
            self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')
    
    ##Start of beginning
    #Initial setup
    pdf = PDF()
    pdf.add_page()
    #Add title
    pdf.set_font('Helvetica', 'B', 24)
    pdf.cell(0, 10, 'Analysis report', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.ln(10)
    #Report
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Table of contents:', new_x='LMARGIN', new_y='NEXT')

    #Function for crating a table from a dataframe
    def create_table(dataframe, title):
        #Add title
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, title, new_x='LMARGIN', new_y='NEXT')
        #Add data
        pdf.set_font('Helvetica', '', 12)
        headers = dataframe.columns.values.tolist()
        data_with_headers = [headers] + dataframe.values.tolist()
        with pdf.table() as table:
            for data_row in data_with_headers:
                row = table.row()
                for datum in data_row:
                    row.cell(str(datum))

    def add_anomalies(anomalies):
        pdf.add_page()
        #Add title
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Anomalies', new_x='LMARGIN', new_y='NEXT')
        #Add data
        pdf.set_font('Helvetica', '', 12)
        for anomaly in anomalies:
            pdf.cell(0, 10, str(anomaly), new_x='LMARGIN', new_y='NEXT')

    #Function that creates a table with the device info
    def add_known_ip(data:list):
        if data:
            #Add title
            pdf.set_font('Helvetica', 'B', 14)
            pdf.cell(0, 10, 'Known IP addresses', new_x='LMARGIN', new_y='NEXT')
            #Add data
            for row in data:
                pdf.set_font('Helvetica', 'B', 12)
                pdf.cell(0, 10, f'{row["ip"]}', new_x='LMARGIN', new_y='NEXT')
                pdf.set_font('Helvetica', '', 12)
                pdf.cell(0, 10, f'Name: {row["name"]}', new_x='LMARGIN', new_y='NEXT')
                pdf.cell(0, 10, f'MAC: {row["mac"]}', new_x='LMARGIN', new_y='NEXT')
                pdf.cell (0, 10, '', new_x='LMARGIN', new_y='NEXT')


    #Function that creates a table with the device info
    def add_device_info():
        #Creates a table with the device info 
        create_table(device_info, 'Device info')
       

    def add_common_messages(df):
        pdf.add_page()
        commmon = df.sort_values(by=['Occurrences'], ascending=False).head(10)
        #Add title
        pdf.set_font('Helvetica', 'B', 18)
        pdf.cell(0, 10, 'Most common messages', new_x='LMARGIN', new_y='NEXT')
        #Add data
        for _, row in commmon.iterrows():
            pdf.set_font('Helvetica', 'B', 12)
            pdf.multi_cell(0, 10, f'{row[1]}: {row[2]}', new_x='LMARGIN', new_y='NEXT')
            pdf.set_font('Helvetica', '', 12)
            pdf.cell(0, 10, f'Occurrences: {row[4]}', new_x='LMARGIN', new_y='NEXT')
            first, last = find_time_span(string_to_list(row[0]))
            pdf.cell(0, 10, f'First time: {first}', new_x='LMARGIN', new_y='NEXT')
            pdf.cell(0, 10, f'Last time: {last}', new_x='LMARGIN', new_y='NEXT')
            pdf.cell(0, 10, '', new_x='LMARGIN', new_y='NEXT')

    def add_least_common_messages(df):
        pdf.add_page()
        least_common = df.sort_values(by=['Occurrences'], ascending=True).head(10)
        #Add title
        pdf.set_font('Helvetica', 'B', 18)
        pdf.cell(0, 10, 'Least common messages', new_x='LMARGIN', new_y='NEXT')
        #Add data
        for _, row in least_common.iterrows():
            pdf.set_font('Helvetica', 'B', 12)
            pdf.multi_cell(0, 10, f'{row[1]}: {row[2]}', new_x='LMARGIN', new_y='NEXT')
            pdf.set_font('Helvetica', '', 12)
            pdf.cell(0, 10, f'Occurrences: {row[4]}', new_x='LMARGIN', new_y='NEXT')
            first, last = find_time_span(string_to_list(row[0]))
            pdf.cell(0, 10, f'First time: {first}', new_x='LMARGIN', new_y='NEXT')
            pdf.cell(0, 10, f'Last time: {last}', new_x='LMARGIN', new_y='NEXT')
            pdf.cell(0, 10, '', new_x='LMARGIN', new_y='NEXT')

    def add_common_ip():
        pdf.set_font('Helvetica', 'B', 18)
        pdf.cell(0, 10, 'Most common IP addresses', new_x='LMARGIN', new_y='NEXT')
    
        ##Add Graphics
        #Total highest
        #Add image
        pdf.image(f'{output_folder}\\visualisations\\most_common_ip.png', x=10, y=pdf.get_y(), w=180)
        pdf.cell(0, 135, '', new_x='LMARGIN', new_y='NEXT')
        add_known_ip(known_total_max)
        pdf.add_page()

        #Per Hour heighest
        #Add image
        pdf.image(f'{output_folder}\\visualisations\\most_common_ip_perHour.png', x=10, y=pdf.get_y(), w=180)
        pdf.cell(0, 135, '', new_x='LMARGIN', new_y='NEXT')
        add_known_ip(known_perHour_max)
        pdf.add_page()


        ##Add table
        create_table(ip_counter, 'Most common IP addresses (table)')

    def add_vpn(VPNcoordinates):
        pdf.add_page()
        #Add title
        pdf.set_font('Helvetica', 'B', 18)
        pdf.cell(0, 10, 'VPN connections', new_x='LMARGIN', new_y='NEXT')
        #Add map
        pdf.image(f'{output_folder}\\visualisations\\vpn_map.png', x=10, y=pdf.get_y(), w=180)
        pdf.cell(0, 135, '', new_x='LMARGIN', new_y='NEXT')
        create_table(VPNcoordinates, 'VPN connections (table)')
        
        

    #Call functions
    add_device_info()
    add_common_messages(df)
    add_least_common_messages(df)
    add_common_ip()
    if anomalies: add_anomalies(anomalies)
    if VPNcoordinates is not None: add_vpn(VPNcoordinates)
    #Output pdf
    pdf.output(f'{output_folder}\\{output_folder}.pdf')


#Function that returns a short string with the date and time
def get_date_time():
    now = datetime.now()
    date_time = now.strftime("%d-%m-%Y_%H-%M-%S")
    return date_time

#Function that creates the output folder
def create_output_folder(filetype):
    date_time = get_date_time()
    output_folder = f'{filetype}_analyzed_{date_time}'
    num = 1
    while os.path.exists(output_folder):
        output_folder = f'{output_folder}_{num}'
        num += 1
    os.makedirs(f'{output_folder}\\visualisations')
    print(f'Contents are saved to: {output_folder}')
    return output_folder

#Creates a SHA256 hash for all files in folder and saves it to a file
def create_hash(folder):
    def add_to_file(path):
        with open(f'{path}\\{file}', 'rb') as f2:
            md5 = hashlib.file_digest(f2, 'md5')
            sha256 = hashlib.file_digest(f2, 'sha256')
            f.write(f'{file}:\n')
            f.write(f'MD5: {md5.hexdigest()}\n')
            f.write(f'SHA256: {sha256.hexdigest()}\n')
            f.write('\n')

    with open(f'{folder}\\hashes.txt', 'w') as f:
        for file in os.listdir(folder):
            #Check if file is a folder
            if os.path.isdir(f'{folder}\\{file}'):
                sub_folder = f'{folder}\\{file}'
                #If it is a folder, create a hash for all files in the folder
                for file in os.listdir(sub_folder):
                    add_to_file(sub_folder)
            else: add_to_file(folder)



def main():
    print('Importing data')
    #Get variables
    path = sys.argv[1]

    #import data
    file_type = extract_file_type(path)

    try:
        device_info = import_csv(f'{path}\\device_info.csv')
    except FileNotFoundError:
        print('No device info found')
        device_info = None

    try:
        messages = import_csv(f'{path}\\messages.csv')
    except FileNotFoundError:
        print('No messages found')
        messages = None
    try:
        vpn = import_csv(f'{path}\\vpn.csv')
    except FileNotFoundError:
        print('No VPN data found')
        vpn = None

    print('Generating output folder')
    #Create output folder
    output_folder = create_output_folder(file_type)

    print('Starting analysis')
    #Get anomalies
    anomalies = detect_anomalies(messages)

    ##Generate visualisations
    #Set number of IPs to show in chart of most common IPs
    IPs_in_chart = 10
    #Get most common IPs
    ip_counter = common_ip(messages)
    #Generate visuals
    known_total_max, known_perHour_max = most_common_ip_visual(ip_counter, device_info, IPs_in_chart, output_folder)

    #Generate VPN map
    apiKey = '308df0dbb1b4475892840ef712ea1814'
    if vpn is not None:
        print('Generating VPN map')
        coordinates = get_coordinates(vpn, apiKey)
        generate_vpn_map(coordinates, output_folder)
        coordinates = reduce_coordinates(coordinates)
    else: coordinates = None

    print('Creating report')
    create_pdf(messages, device_info, ip_counter, known_total_max, known_perHour_max, anomalies, coordinates, file_type, output_folder)

    print('Creating hash')
    #Creates a file with hashes of all files in the output folder
    create_hash(output_folder)

    print('Done!')

if __name__ == '__main__':
    main()