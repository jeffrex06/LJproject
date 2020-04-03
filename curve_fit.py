import pyodbc
import pandas as pd
from scipy.optimize import curve_fit
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
import time


def read_in_csv(file_path):
  
    dataframe=pd.read_csv(file_path)
    return dataframe

def hyperbolic_equation(t, qi, di):

    #return qi/((1.0+b*di*t)**(1.0/b))
    return qi/((1.0+1.2*di*t)**(1.0/1.2))
    

def exponential_equation(t, qi, di):

    return qi*np.exp(-di*t)

def remove_nan_and_zeroes_from_columns(df, variable):

    filtered_df = df[(df[variable].notnull()) & (df[variable]>0)]
    return filtered_df

def generate_time_delta_column(df, time_column, date_first_online_column):

    return (df[time_column]-df[date_first_online_column]).dt.days
    
def get_min_or_max_value_in_column_by_group(dataframe, group_by_column, calc_column, calc_type):

    value=dataframe.groupby(group_by_column)[calc_column].transform(calc_type)
    return value

def get_max_initial_production(df, number_first_months, variable_column, date_column):

    #First, sort the data frame from earliest to most recent prod date
    df=df.sort_values(by=date_column)
    #Pull out the first x months of production, where number_first_months is x
    df_beginning_production=df.head(number_first_months)
    #Return the max value in the selected variable column from the newly created 
    #df_beginning_production df
    return df_beginning_production[variable_column].max()

def plot_actual_vs_predicted_by_equations(df, x_variable, y_variables, plot_title):
    """
    This function is used to map x- and y-variables against each other
    Arguments:
        df: Pandas dataframe.
        x_variable: String. Name of the column that we want to set as the 
        x-variable in the plot
        y_variables: string (single), or list of strings (multiple). Name(s) 
        of the column(s) that we want to set as the y-variable in the plot
    """
    #Plot results
    df.plot(x=x_variable, y=y_variables, title=plot_title)
    plt.show()

def main():

    pdf = PdfPages("C:/Python_Scripts/Curve_Fit/Auto_Forecast.pdf")
    
    #Read in the monthly oil and gas data
    xls = pd.ExcelFile('Original Access DB.xlsx')
    all_data = pd.read_excel(xls, 'Product')
    eco_data = pd.read_excel(xls, 'Economic')
    
    #Perform some data cleaning to get the columns as the right data type
    all_data['P_DATE']=pd.to_datetime(all_data['P_DATE'])
    #Declare the desired product that we want to curve fit for--it can either by 'Gas' or 'Oil'
    desired_product_type='OIL'
    #Remove all rows with null values in the desired time series column
    all_data=remove_nan_and_zeroes_from_columns(all_data, desired_product_type)
    #Get the earliest RecordDate for each Propnum
    all_data['Online_Date']= get_min_or_max_value_in_column_by_group(all_data, group_by_column='PROPNUM', 
                  calc_column='P_DATE', calc_type='min')
    #Generate column for time online delta
    all_data['Days_Online']=generate_time_delta_column(all_data, time_column='P_DATE', 
                  date_first_online_column='Online_Date')
    #Pull data that came online between January and June 2016
    #bakken_data_2016=bakken_data[(bakken_data.Online_Date>='2016-01-01') & (bakken_data.Online_Date<='2016-06-01')]
    
    #Get a list of unique API's to loop through--these were randomly selected as examples
    PROPNUM_list=all_data['PROPNUM'].unique()
    di_data=list()
    qi_data=list()
    #Loop through each API, and perform calculations
    for PROPNUM in PROPNUM_list:
        #Subset the dataframe by API Number
        production_time_series=all_data[all_data.PROPNUM==PROPNUM]
        
        
########################################### oil ############################################################################
        desired_product_type='OIL'
        #Monthlength=production_time_series.iloc[1][7]
        length=len(production_time_series.index)
        if length>12:
            production_time_series2=production_time_series.tail(int(length*.5))
        else:
            production_time_series2=production_time_series
        if PROPNUM=='V3UJ4MUCIK':
            print(PROPNUM)
            
        if length<2:
            
            qi=100
            di=1
        else:
            Start_Date=production_time_series.iloc[1][6]
            Start_Date=str(datetime.date(Start_Date).strftime('%m/%Y'))
            #print(PROPNUM)
            #Monthlength=production_time_series.iloc[1][7]
            #Get the highest value of production in the first three months of production, to use as qi value
            qi=get_max_initial_production(production_time_series, 4, desired_product_type, 'P_DATE')
           
            
            #Hyperbolic curve fit the data to get best fit equation
            popt_hyp, pcov_hyp=curve_fit(hyperbolic_equation, production_time_series2['Days_Online'], 
                                         production_time_series2[desired_product_type],bounds=([qi*.75,.001], [qi*1.4,97]))
            
            
            qi=popt_hyp[0]
            di=popt_hyp[1]
            #Convert to Aries Di
            di=(qi-(qi/((1+1.2*di*365)**(1/1.2))))/qi
            
            
           # print('Hyperbolic Fit Curve-fitted Variables: qi='+str(qi)+', b=1.2, di='+str(di))
    
            #Hyperbolic fit results
            production_time_series.loc[:,'Hyperbolic_Predicted']=hyperbolic_equation(production_time_series['Days_Online'], 
                                      *popt_hyp)
    
            #Declare the x- and y- variables that we want to plot against each other
#            y_variables=[desired_product_type, "Hyperbolic_Predicted"]
#            x_variable='Days_Online'
            #Create the plot title
#            plot_title=desired_product_type+' Production for Well API '+str(PROPNUM)
#            #Plot the data to visualize the equation fit
#            plot_actual_vs_predicted_by_equations(production_time_series, x_variable, y_variables, plot_title)
            
            plt.style.use('seaborn-bright')
            fig, ax = plt.subplots()
            production_time_series.plot(kind='line',x='Days_Online',y='OIL',color='green', ax=ax, label='Oil Production')
            production_time_series.plot(kind='line',x='Days_Online',y='Hyperbolic_Predicted',linestyle='--' ,color='green', ax=ax, label='Oil Forecast')
            ax.set_title(PROPNUM+' Qi='+str(int(qi/31))+' Di='+str(int(di*100)))
            
            plt.savefig(pdf, format='pdf', bbox_inches='tight')
            plt.close('all')
        
        
        update_row=eco_data[(eco_data['PROPNUM'] == PROPNUM) & (eco_data['QUALIFIER'] == 'CASHFLOW') & (eco_data['KEYWORD'] == 'OIL')]
        if len(update_row)>0:
            s=update_row.iloc[0]['EXPRESSION']
            s=s[s.find("X B/D"):]
            s=str(int(qi/31))+" "+s
            s=s[:s.find("B/1.2")]
            s=s+"B/1.2 "+str("{0:.1f}".format(di*100))
            index=update_row.index.values.astype(int)[0]
            #Update Economic Table
            eco_data.set_value(index,'EXPRESSION',s)
            eco_data.set_value(index-1,'EXPRESSION',Start_Date)
        
        qi_data.append(int(qi/31))
        di_data.append("{0:.1f}".format(di*100))
        
      
        
################################################## GOR ##############################################################################
        
        production_time_series=remove_nan_and_zeroes_from_columns(production_time_series, 'GAS')
        production_time_series['GOR']=production_time_series['GAS']*1000/production_time_series['OIL']
        length=len(production_time_series.index)
        if length>6:
            production_time_series2=production_time_series.tail(6)
            aveGOR=production_time_series2['GOR'].mean()
            finalGOR=str("{0:.2f}".format((aveGOR+500)/1000))
            aveGOR=str("{0:.2f}".format(aveGOR/1000))

        elif length>0:
            production_time_series2=production_time_series
            aveGOR=production_time_series2['GOR'].mean()
            finalGOR=str("{0:.2f}".format((aveGOR+500)/1000))
            aveGOR=str("{0:.2f}".format(aveGOR/1000))            
        else:
            aveGOR=str("{0:.2f}".format(.01/1000))  
            
        

        
        update_row=eco_data[(eco_data['PROPNUM'] == PROPNUM) & (eco_data['QUALIFIER'] == 'CASHFLOW') & (eco_data['KEYWORD'] == 'GAS/OIL')]
        index=update_row.index.values.astype(int)[0]
        
        if eco_data.iloc[index+1]['KEYWORD']=='"':
            if eco_data.iloc[index+2]['KEYWORD']=='"':
                s1=eco_data.iloc[index]['EXPRESSION']
                s1=s1[s1.find(" M/B "):]
                s1=aveGOR+" "+aveGOR+" "+s1
                eco_data.set_value(index,'EXPRESSION',s1)
                
                s2=eco_data.iloc[index+1]['EXPRESSION']
                s2=s2[s2.find(" M/B "):]
                s2=aveGOR+" "+aveGOR+" "+s2
                eco_data.set_value(index+1,'EXPRESSION',s2)
                
                s3=eco_data.iloc[index+2]['EXPRESSION']
                s3=s3[s3.find(" M/B "):]
                s3=aveGOR+" "+aveGOR+" "+s3
                eco_data.set_value(index+2,'EXPRESSION',s3)
            else:
                s1=eco_data.iloc[index]['EXPRESSION']
                s1=s1[s1.find(" M/B "):]
                s1=aveGOR+" "+aveGOR+" "+s1
                eco_data.set_value(index,'EXPRESSION',s1)
                
                s2=eco_data.iloc[index+1]['EXPRESSION']
                s2=s2[s2.find(" M/B "):]
                s2=aveGOR+" "+aveGOR+" "+s2
                eco_data.set_value(index+1,'EXPRESSION',s2)
        else:
            s1=eco_data.iloc[index]['EXPRESSION']
            s1=s1[s1.find(" M/B "):]
            s1=aveGOR+" "+aveGOR+" "+s1
            eco_data.set_value(index,'EXPRESSION',s1)
        
#########################################Water################################################################################
        desired_product_type='WATER'
        #Monthlength=production_time_series.iloc[1][7]
        production_time_series=remove_nan_and_zeroes_from_columns(production_time_series, desired_product_type)
        length=len(production_time_series.index)
        
        if length>12:
            production_time_series2=production_time_series.tail(int(length*.2))
        else:
            production_time_series2=production_time_series
            
        length=len(production_time_series.index)            
            
        if length<2:
            qi=100
            di=1
        else:
            Monthlength=production_time_series.iloc[1][7]
            #Get the highest value of production in the first three months of production, to use as qi value
            qi=get_max_initial_production(production_time_series, 4, desired_product_type, 'P_DATE')
           
            
            #Hyperbolic curve fit the data to get best fit equation
            popt_hyp, pcov_hyp=curve_fit(hyperbolic_equation, production_time_series2['Days_Online'], 
                                         production_time_series2[desired_product_type],bounds=([qi*.75,.0001], [qi*1.1,100]))
        
        
            qi=popt_hyp[0]
            di=popt_hyp[1]
            #Convert to Aries Di
            di=(qi-(qi/((1+1.2*di*365)**(1/1.2))))/qi
            
            
    
            #Hyperbolic fit results
            production_time_series.loc[:,'Hyperbolic_Predicted']=hyperbolic_equation(production_time_series['Days_Online'], 
                                      *popt_hyp)
    
            #Declare the x- and y- variables that we want to plot against each other
#            y_variables=[desired_product_type, "Hyperbolic_Predicted"]
#            x_variable='Days_Online'
#            #Create the plot title
#            plot_title=desired_product_type+' Production for Well API '+str(PROPNUM)
#            #Plot the data to visualize the equation fit
#            plot_actual_vs_predicted_by_equations(production_time_series, x_variable, y_variables, plot_title)
            
            plt.style.use('seaborn-bright')
            fig, ax = plt.subplots()
            production_time_series.plot(kind='line',x='Days_Online',y='WATER',color='blue', ax=ax, label='Water Production')
            production_time_series.plot(kind='line',x='Days_Online',y='Hyperbolic_Predicted',linestyle='--' ,color='blue', ax=ax, label='Water Forecast')
            ax.set_title(PROPNUM+' Qi='+str(int(qi/31))+' Di='+str(int(di*100)))
            
            plt.savefig(pdf, format='pdf', bbox_inches='tight')
            plt.close('all')
        
        
        update_row=eco_data[(eco_data['PROPNUM'] == PROPNUM) & (eco_data['QUALIFIER'] == 'CASHFLOW') & (eco_data['KEYWORD'] == 'WTR')]
        s=update_row.iloc[0]['EXPRESSION']
        s=s[s.find("X B/D"):]
        s=str(int(qi/31))+" "+s
        s=s[:s.find("B/1.2")]
        s=s+"B/1.2 "+str("{0:.1f}".format(di*100))
        index=update_row.index.values.astype(int)[0]
        #Update Economic Table
        eco_data.set_value(index,'EXPRESSION',s)
        
        

    writer = pd.ExcelWriter("New_Economic.xlsx", engine='xlsxwriter')
    eco_data.to_excel(writer, index=False, sheet_name='New_ECONOMIC')
    
    
    plt.hist(di_data, color = 'blue', edgecolor = 'black', bins = 5)
    plt.xticks(fontsize=9)
    plt.xticks(rotation=90)
    plt.savefig(pdf, format='pdf', bbox_inches='tight')
    plt.close('all')
    plt.hist(qi_data, color = 'blue', edgecolor = 'black', bins = 5)
    plt.xticks(fontsize=9)
    plt.xticks(rotation=90)
    plt.savefig(pdf, format='pdf', bbox_inches='tight')
    plt.close('all')
    plt.clf()
    pdf.close()        
        
        
                
if __name__== "__main__":
    main()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    