import sys
import pandas
import matplotlib.pyplot as plt

#Function that imports a csv file and returns a pandas dataframe
def import_csv(path):
    data = pandas.read_csv(path)
    return data

#Function that extracts the file type from the path
def extract_file_type(path):
    file_type = path.split('/')[-1]
    file_type = file_type.split('\\')[-1]
    file_type = file_type.split('.')[0].split('_')[0]
    return file_type

#Function that makes a bar chart from a pandas dataframe with matplotlib
def make_bar_chart(dataframe, x_axis, y_axis, title, x_label, y_label, save_path):
    colors = ['red', 'green', 'blue', 'yellow', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
    plt.bar(dataframe[x_axis], dataframe[y_axis], color=colors)
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.savefig(save_path)

def main():
    path = sys.argv[1]
    file_type = extract_file_type(path)
    df = import_csv(path)

if __name__ == '__main__':
    main()