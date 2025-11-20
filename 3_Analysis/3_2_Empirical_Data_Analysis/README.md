RAWDATA是接收到的未经任何处理过的数据


RAWDATA1是更改了命名规则，整理了命名规则的数据



Detection rate.rmd 是检出率的R文件



EGA.rmd 是EGA的R文件



预处理是将RAWDATA1和Complains\_YoungClients进行处理的代码，处理规则如下：
在本研究的数据预处理中，Rawdata1.xlsx 与 Complains\_YoungClients.xls 两个数据表均包含重复的 ID。

为了确保后续分析中每个 ID 仅保留一条最合适的记录，我们制定并实施了如下匹配与筛选规则：

1\. 两个数据表均出现的 ID（共同 ID）

当某个 ID 同时存在于 Rawdata1 与 Complains 数据表中，且各自都可能有多条记录时：

规则：找到 Raw 中每条记录与 Complains 中每条记录之间的时间差，保留时间差最小的那一对。

Raw 表使用字段：提交时间（parsed datetime）

Complains 表使用字段：就诊日期（parsed datetime）

对所有组合计算时间差（绝对值，单位秒）

选择时间差最小的一对

仅保留这一行 Raw 及这一行 Complains

其余记录全部删除

这样保证共同 ID 在两个文件中都仅保留 最匹配的、最接近的时间点。

2\. 仅在 Rawdata1 中出现的 ID

当某个 ID 出现在 Rawdata1 中，但 不出现在 Complains 中时：

规则：保留 Rawdata1 中该 ID 的所有记录里 “提交时间最早” 的一条。

同时删除该 ID 的其他记录

这样保证 Raw 中的独有 ID 也只保留一条最合理的数据。

3\. 仅在 Complains\_YoungClients 中出现的 ID

当某个 ID 出现在 Complains 中，但 不出现在 Rawdata1 中时：

规则：保留 Complains 中该 ID 的所有记录里 “就诊日期最早” 的一条。

同时删除该 ID 的其他记录

这保证 Complains 中的独有 ID 也只保留一条最代表性的记录。

输出数据文件为：Raw\_output.xlsx 也是后续检出率和EGA载入的数据文件。



RAWDATA: The raw data received without any preprocessing.



RAWDATA1: The data with revised naming conventions and cleaned up naming rules.



Detection rate.rmd: R script for detection rate analysis.



EGA.rmd: R script for EGA (Exploratory Graph Analysis).

During data preprocessing, both Rawdata1.xlsx and Complains\_YoungClients.xls contain repeated IDs. To ensure that each ID corresponds to only one valid record in subsequent analyses, the following matching and filtering rules were applied:

1\. IDs that appear in both datasets (Common IDs)

If an ID exists in both Rawdata1 and Complains, and each dataset may contain multiple records for that ID:

Rule: Identify the pair of records — one from Rawdata1 and one from Complains — whose timestamps are the closest to each other, and retain only this pair.

Raw timestamp: Submission Time (parsed datetime)

Complains timestamp: Visit Date (parsed datetime)

Compute the absolute time difference (in seconds) for all possible combinations

Select the pair with the smallest time difference

Retain only this matched pair

Remove all other records for that ID in both datasets

This ensures that each common ID is represented by the most temporally consistent pair of records.

2\. IDs that appear only in Rawdata1

If an ID is present in Rawdata1 but not in Complains:

Rule: Retain only the record with the earliest submission time from Rawdata1.

All other records for that ID are removed.

This ensures that Raw-only IDs are represented in the clean dataset without duplication.

3\. IDs that appear only in Complains\_YoungClients

If an ID is present in Complains but not in Rawdata1:

Rule: Retain only the record with the earliest visit date from Complains.

All other records for that ID are removed.

This ensures that Complains-only IDs also retain a single representative record.

