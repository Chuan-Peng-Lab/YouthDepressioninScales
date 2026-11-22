# 1. 安装并加载读取 Excel 的包（只需首次安装）
if (!requireNamespace("readxl", quietly = TRUE)) {
  install.packages("readxl")
}

# 2. 手动选择总表文件，读取 Sheet1
dat <- readxl::read_excel(file.choose(), sheet = "Sheet1")

# 检查必需的列
required_cols <- c(
  "Item", "pyy", "qjy", "qjy&pyy",
  "mjy", "why", "why&mjy"
)

if (!all(required_cols %in% names(dat))) {
  stop("表格缺少必需列，请检查列名是否正确。")
}

# 仅保留有条目编号的行
dat <- dat[
  !is.na(dat$Item) & trimws(as.character(dat$Item)) != "",
]

if (nrow(dat) == 0L) stop("没有可计算的条目。")
if (anyDuplicated(dat$Item)) stop("Item 存在重复，请先核对条目。")


# 3. 定义计算函数
calculate_kappa <- function(a, b, comparison) {
  
  # 转为文字，将 NA 统一为空字符串，去掉首尾空白
  clean_label <- function(x) {
    x <- as.character(x)
    x[is.na(x)] <- ""
    trimws(x, whitespace = "[\\h\\v]")
  }
  
  a <- clean_label(a)
  b <- clean_label(b)
  
  stopifnot(length(a) == length(b))
  n <- length(a)
  
  # 实际一致：双方非空，且整个标签完全相同
  agree <- sum(a != "" & b != "" & a == b)
  po <- agree / n
  
  # 统计双方各个非空标签的频数
  categories <- union(a[a != ""], b[b != ""])
  
  freq_a <- as.numeric(table(factor(a, levels = categories)))
  freq_b <- as.numeric(table(factor(b, levels = categories)))
  
  # 空白不作为共同类别；总分母仍保留所有条目
  chance_sum <- sum(freq_a * freq_b)
  pe <- chance_sum / n^2
  
  # Pe = 1 时，κ 的分母为 0，无法定义
  kappa <- if (pe == 1) NA_real_ else (po - pe) / (1 - pe)
  
  data.frame(
    比较 = comparison,
    总条目数 = n,
    一致条目数 = agree,
    不一致条目数 = n - agree,
    A方空白数 = sum(a == ""),
    B方空白数 = sum(b == ""),
    频数乘积之和 = chance_sum,
    Po = po,
    Pe = pe,
    Kappa = kappa,
    check.names = FALSE
  )
}


# 4. 分别计算三组结果
results <- rbind(
  calculate_kappa(
    dat[["pyy"]], dat[["qjy"]],
    "第一组：pyy 与 qjy"
  ),
  calculate_kappa(
    dat[["mjy"]], dat[["why"]],
    "第二组：mjy 与 why"
  ),
  calculate_kappa(
    dat[["qjy&pyy"]], dat[["why&mjy"]],
    "组间：qjy&pyy 与 why&mjy"
  )
)

# 显示详细结果，保留六位小数
display_results <- results
display_results[c("Po", "Pe", "Kappa")] <-
  round(display_results[c("Po", "Pe", "Kappa")], 6)

print(display_results, row.names = FALSE)

# 显示论文中使用的三位小数结果
cat(
  sprintf(
    "\n第一组组内 κ = %.3f\n第二组组内 κ = %.3f\n组间 κ = %.3f\n",
    results$Kappa[1],
    results$Kappa[2],
    results$Kappa[3]
  )
)