###############################library packages#############################
#base
#install.packages('tidyverse')
#install.packages('bruceR')
library('tidyverse')
library('bruceR')

#plot
#install.packages('ggplot2')
library('ggplot2')

#color
#install.packages('viridisLite')
#install.packages('viridis')
library('viridisLite')
library('viridis')
#if you use mac OS, you should change the path of font file
#default: simsun.ttc (songti)

#Figure1.pdf display Chinese
#install.packages('showtext')
#install.packages('Cairo')
#install.packages('sysfonts')
#install.packages('showtextdb')
library('sysfonts')
library('showtextdb')
library('showtext')
library('Cairo')

#################################edit here##################################

#set working path
setwd("C:/Users/hmz19/Desktop/YuKi's Projects/Mental Health/task/task15/OUTPUT")
#open matrix
rawdata = bruceR::import("C:\\Users\\hmz19\\Desktop\\YuKi's Projects\\Mental Health\\task\\task15\\data\\depression_matrix_a_0.xlsx")  #Load data for plot (difference between specific and compound symptoms)
  #the structure of matrixA: 
  #first row: scale_name_1, scale_name_2, scale_name_3,...,scale_name_n,S_name
  #...
  #each row represents a symptom
  #each column represents a scale

#setting the number of scales and symptoms 
n_scales = 26 #number of scales
n_symptoms = 84 #number of symptoms

#ordered by number of symptoms
order_data = rawdata %>%
  dplyr::mutate(count = rowSums(across(where(is.numeric)), na.rm=TRUE)) %>%
  dplyr::arrange(.,desc(count)) %>%
  dplyr::select(.,-count)

##############################create function ##############################
#######################click 2 times and get your graph#####################
matrixA_plot <- function(dataplot,n_scal,n_symp){
  set.seed(223)
  d <- dataplot %>%
    dplyr::select(.,-S_name) %>%
    dplyr::mutate(.,S = paste(1:nrow(dataplot),sep = "")) %>%
    melt(., id.vars="S", variable.name="Scales", value.name="Type") %>%
    dplyr::filter(.,Type >= 1) %>%
    dplyr::mutate(.,Type = ifelse(Type==1,"Scale contains compound symptom","Scale contains specific symptom")) %>%
    dplyr::mutate(.,S=as.numeric(S))
    
  symp <- dataplot %>%
    dplyr::mutate(.,S=1:nrow(.)) %>%
    dplyr::mutate(S_name = factor(S_name,levels = .$S_name))  %>%
    dplyr::select(S,S_name)
    
  #levels(symp$S_name)
    
  num = d %>%
    dplyr::mutate(n=1) %>%
    dplyr::group_by(Scales) %>%
    dplyr::summarise(.,count = sum(n)) %>%
    dplyr::ungroup() %>%
    dplyr::arrange(.,desc(count)) %>%
    dplyr::mutate(order=1:nrow(.))
    
    
  plot = dplyr::full_join(num, d, by = "Scales") %>%
    dplyr::mutate(Scales2=order) %>%
    dplyr::mutate(Scales = factor(Scales,levels = num$Scales))  %>%
    dplyr::mutate(S = factor(S,levels = symp$S,labels = symp$S_name))  %>%
    dplyr::select(S,Scales,Scales2,Type)
    
  #levels(plot$Scales)
    
  # Plot
  pal_rb<- viridis(n_scal,option = "H")
  #font setting
  showtext::showtext.auto(enable = T)
  font_add(family = "songti",regular = "C:/Windows/Fonts/simsun.ttc") 
    #add font = songti, otherwise, the Chinese cannot be displayed in pdf
    
    
  a<- ggplot(plot, aes(x=S, y=Scales2, group=S, color=Scales, shape=Type, rev=F)) +
    geom_line() + #keep this here, otherwise there is an error 
    xlab("") +
    ylab("") +
    # Generate the grid lines
    geom_hline(yintercept = 1:n_scal, colour = "grey80", size = .2) +
    geom_vline(xintercept = 1:n_symp, colour = "grey80", size = .2) +
    # Points and lines
    geom_line(colour="grey60") +
    geom_point(size=3, fill="white") +
    # Fill the middle space with a white blank rectangle
    geom_rect(xmin=-Inf,xmax=Inf,ymin=-Inf,ymax=.6,fill="white", color=NA) +
    # Polar coordinates 
    #circle or not
    #coord_polar() +
    scale_shape_manual(values=c(21,19)) +
    # The angle for the symptoms and remove the default grid lines
    theme(axis.text.x = element_text(angle=90, hjust=1,vjust = 0),
          axis.text.y = element_text(angle=120, hjust=0,vjust = 0),
          panel.border = element_blank(),
          axis.line = element_blank(),
          axis.ticks = element_blank(),
          panel.grid = element_blank(),
          panel.background = element_blank(),
          legend.position="right",
          plot.margin = unit(rep(.5,4), "lines"),
          text = element_text(family="songti",size=20)) +
    labs(fill="") + # remove legend title
    scale_y_continuous(limits=c(0,n_scal+3), expand=c(0,0), breaks=1:n_scal, labels=levels(plot$Scales))+
    scale_color_manual(values=pal_rb);  
    
    ggsave(plot=a,filename="Figure1.pdf", width = 25, height = 17)
    # Figure 1 was further adjusted in Inkscape
    
return(a)
}

matrixA_plot(dataplot = order_data,
             n_scal = n_scales,
             n_symp = n_symptoms)  
