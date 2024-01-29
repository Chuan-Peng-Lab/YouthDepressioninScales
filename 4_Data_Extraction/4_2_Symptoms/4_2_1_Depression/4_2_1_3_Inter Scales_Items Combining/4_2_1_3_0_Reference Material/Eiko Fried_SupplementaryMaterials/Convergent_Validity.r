######################################################################################
#####                                                                            ##### 
#####   Supplementary material for Fried 2016, Journal of Affective Disorders    ##### 
#####                                                                            ##### 
#####                 Calculation of convergent validity based on                #####
#####                   inter-item correlation and scale length                  #####
#####                                                                            ##### 
######################################################################################


# Thanks for assistance with this calculation to Sophie van der Sluis, section Complex Trait Genetics, VU/VUmc Amsterdam, the Netherlands

k <- 20     # number of items in each of 2 scales
x <- 0.1    # inter-item correlation 

m1=matrix(x,k,k)
m2=matrix(x,k,k)
diag(m1)=1
var1=var2=sum(m1)
covar=sum(m2)

covar/(sqrt(var1)*sqrt(var2))  # sum-score correlation among scales


