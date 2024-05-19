from pdf2image import convert_from_path

# PDF文件路径
pdf_path = 'Survey-summary.pdf'

# 转换PDF
images = convert_from_path(pdf_path)

# 保存图像
for i, image in enumerate(images):
    image.save(f'page_{i}.png', 'PNG')
