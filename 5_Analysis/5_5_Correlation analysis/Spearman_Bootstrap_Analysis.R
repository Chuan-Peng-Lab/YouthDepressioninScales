# 自动检查并安装缺失的包
required_packages <- c("haven", "boot")

for (package in required_packages) {
  if (!require(package, character.only = TRUE)) {
    install.packages(package, dependencies = TRUE)
    library(package, character.only = TRUE)
  }
}

#导入数据
data <- bruceR::import(here::here("data", "相关12.28.sav"))

# 定义自举函数
bootstrap_corr <- function(data, indices, var1, var2) {
  d <- data[indices, ]
  return(cor(d[[var1]], d[[var2]], method = "spearman"))
}

# 计算并打印三组斯皮尔曼相关系数及其自举置信区间
pairs <- list(c("symptom", "length"), c("symptom", "Meanoverlap"), c("length", "Meanoverlap"))

for (pair in pairs) {
  var1 <- pair[1]
  var2 <- pair[2]
  
  # 计算斯皮尔曼相关
  spearman_corr <- cor(data[[var1]], data[[var2]], method = "spearman")
  
  # 进行2000次自举
  set.seed(123)
  boot_results <- boot(data, function(data, indices) bootstrap_corr(data, indices, var1, var2), R = 2000)
  
  # 获取自举区间
  boot_ci <- boot.ci(boot_results, type = "perc")
  
  # 打印结果
  cat("\n", var1, "and", var2, "Spearman Correlation:", spearman_corr, "\n")
  print(boot_ci)
}
