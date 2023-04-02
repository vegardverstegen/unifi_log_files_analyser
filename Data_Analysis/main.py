import sys
import pandas
import matplotlib.pyplot as plt
from fpdf import FPDF

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
    lst = string.strip('[]').split(', ')
    return lst

#Function that makes a bar chart from a pandas dataframe with matplotlib
def make_bar_chart(dataframe, x_axis, y_axis, title, x_label, y_label, save_path):
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
    ip_counter = pandas.DataFrame(columns=['ip', 'occurrences'])
    #Loop through IP addresses and occurences in the dataframe
    for _, row in dataframe.iterrows():
        IPs = string_to_list(row['IP Address'])
        occurrences = row['Occurrences']
        #Loop through IP addresses on each row
        for i in IPs:
            #Chek if IP exists
            if i:
                #Check if IP address is already in the dataframe row
                if i in ip_counter['ip'].values:
                    #If it is, add the occurrences to the existing row
                    ip_counter.loc[ip_counter['ip'] == i, 'occurrences'] += occurrences
                else:
                    #If it isn't, add a new row
                    ip_counter = pandas.concat([ip_counter, pandas.DataFrame([[i, occurrences]], columns=['ip', 'occurrences'])], ignore_index=True)
    #Sort dataframe by occurrences
    ip_counter = ip_counter.sort_values(by=['occurrences'], ascending=False)
    return ip_counter

#Function that creates a final report in pdf format
def create_pdf(device_info):
    #Initial setup
    pdf = FPDF()
    pdf.add_page()
    #Add title
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 10, 'Analysis report', 0, 1, 'C')
    #Report
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, 'This is a report of the analysis of the data from the UniFi controller.', 0, 1, 'L')

    #Function that creates a table with the device info
    def add_device_info():
        #Add title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Device info', 0, 1, 'L')
        #Creates a talbe with the device info
        #Add headers
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(60, 10, 'Device name', 1, 0, 'L')
        pdf.cell(60, 10, 'IP address', 1, 0, 'L')
        pdf.cell(60, 10, 'MAC address', 1, 1, 'L')
        #Add data
        pdf.set_font('Arial', '', 12)
        for _, row in device_info.iterrows():
            pdf.cell(60, 10, row[0], 1, 0, 'L')
            pdf.cell(60, 10, row[1], 1, 0, 'L')
            pdf.cell(60, 10, row[2], 1, 1, 'L')

    def add_common_ip():
        #Add title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Most common IP addresses', 0, 1, 'L')
        #Add image
        pdf.image('local\\visualisations\\most_common_ip.png', x=10, y=pdf.get_y(), w=180)

      

    #Call functions
    add_device_info()
    add_common_ip()
    #Output pdf
    pdf.output('output.pdf', 'F')


def main():
    #path = sys.argv[1]
    path = 'local\\usgmessages_processed_02-04-2023_20-57-32'
    device_info = import_csv(f'{path}\\device_info.csv')
    file_type = extract_file_type(path)
    df = import_csv(f'{path}\\{file_type}.csv')

    #Visualise the most common IP addresses
    ip_counter = common_ip(df)
    num_of_ip = 10
    make_bar_chart(ip_counter.head(num_of_ip), 'ip', 'occurrences', f'Top {num_of_ip} IP Addresses', 'IP address', 'Occurrences', 'local\\visualisations\\most_common_ip.png')

    create_pdf(device_info)

if __name__ == '__main__':
    main()