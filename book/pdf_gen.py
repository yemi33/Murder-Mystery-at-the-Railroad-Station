import reportlab.pdfgen.canvas
import reportlab.lib.units
import reportlab.platypus
import reportlab.lib.styles


class PDF:
    """A programmatically generated PDF document."""

    def __init__(self, filename, width, height, x_margin=None, y_margin=None, initial_base_style=None,
                 initial_font_name=None, initial_font_size=None, initial_font_color=None):
        """Initialize a PDF object.

        See the ReportLab PDF Library user guide for more info: https://www.reportlab.com/docs/reportlab-userguide.pdf

        Args:
            filename:
                The filename to which this PDF will ultimately be written.
            width:
                The width of the PDF document, in inches. Note: Carleton Print Services can print physical booklets in
                two sizes: 8.5" x 11" or 5.5" x 8.5".
            height:
                The height of the PDF document, in inches.
            x_margin:
                The left and right margin, if any, in inches. If None, defaults to width / 8.0.
            y_margin:
                The top and bottom margin, if any, in inches. If None, defaults to height / 8.0.
            initial_base_style:
                The name of the initial base style, if any, that will be modified by any further declarations, if any.
                If None, defaults to "BodyText". See PDF.style() for a listing of base styles.
            initial_font_name:
                The name of the initial font for this document, if any. If None, defaults to Helvetica. See
                PDF.style() for a listing of supported font names.
            initial_font_name:
                The name of the initial font for this document, if any. If None, defaults to Helvetica. See
                PDF.style() for a listing of supported font names.
            initial_font_size:
                The initial font size for this document, if any, in points. If None, defaults to 16pt.
            initial_font_color:
                The initial font color, if any. If None, defaults to black. See PDF.style() for a listing of
                supported colors.
        """
        self.filename = filename
        # Set width and height
        self.width = width  # Width in inches
        self.height = height  # Height in inches
        # Set margins
        self.x_margin = x_margin or width / 8.0
        self.y_margin = y_margin or height / 8.0
        # Set style attributes (these can all be changed via PDF.style())
        self.font = initial_font_name or 'Helvetica'
        self.font_size = initial_font_size or 16
        self.font_color = initial_font_color or "black"
        self.left_indent = 0
        self.right_indent = 0
        self.alignment = "center"
        self.background_color = None
        self.background_padding = None
        self.leading = self.font_size * 0.85
        self.space_between_paragraphs = 6
        # Set the current style
        self.base_style = initial_base_style or "BodyText"
        self._style = None  # Actual style object
        self.style(base=self.base_style)
        # Prepare the document (this is an instance of the class Canvas)
        self._doc = reportlab.platypus.SimpleDocTemplate(
            filename=filename,
            pagesize=(self.width * reportlab.lib.units.inch, self.height * reportlab.lib.units.inch),
            initialFontName=initial_font_name,
            initialFontSize=initial_font_size,
            leftMargin=self.x_margin * reportlab.lib.units.inch,
            rightMargin=self.x_margin * reportlab.lib.units.inch,
            topMargin=self.y_margin * reportlab.lib.units.inch,
            bottomMargin=self.y_margin * reportlab.lib.units.inch
        )
        # Prepare the PDF contents list
        self._contents = []

    def style(self, base=None, font_name=None, font_size=None, font_color=None, left_indent=None, right_indent=None,
              alignment=None, background_color=None, background_padding=None, leading=None,
              space_between_paragraphs=None):
        """Change the style for this PDF.

        Args:
            base:
                The base style, upon which any other modifications will be made.
            font_name:
                The new font name, if any. If None, defaults to not changing the font.
            font_size:
                The new font size, if any, in points. If None, defaults to not changing the font size.
            font_color:
                The new font color, if any. If None, defaults to not changing the font color.
            left_indent:
                The left indentation of each paragraph, if any, in inches. If 0, the text for each paragraph will
                begin at the left margin of the page.
            right_indent:
                The right indentation of each paragraph, if any, in inches. If 0, the text for each paragraph will
                end at the right margin of the page.
            alignment:
                The alignment for each paragraph. Must be one of {"left", "center", "right", "justify"}.
            background_color:
                The background color, if any, that will appear in a box behind each paragraph.
            background_padding:
                The padding for all four sides of such a box of background color, if any, in points. Padding defines
                the space between the text and the edge of the box of background color.
            leading:
                The vertical spacing between adjacent lines.
            space_between_paragraphs:
                The vertical spacing between adjacent paragraphs, in points.

        Returns:
            None.

        Here's a listing of supported base styles:
            "BodyText"
            "Bullet"
            "Code"
            "Definition"
            "Heading1"
            "Heading2"
            "Heading3"
            "Heading4"
            "Heading5"
            "Heading6"
            "Italic"
            "Normal"
            "OrderedList"
            "Title"
            "UnorderedList"

        Here's a listing of supported font names:
            "Courier"
            "Courier-Bold"
            "Courier-BoldOblique"
            "Courier-Oblique"
            "Helvetica"
            "Helvetica-Bold"
            "Helvetica-BoldOblique"
            "Helvetica-Oblique"
            "Symbol"
            "Times-Bold"
            "Times-BoldItalic"
            "Times-Italic"
            "Times-Roman"
            "ZapfDingbats"

        A listing of supported color names is available here:
                https://hg.reportlab.com/hg-public/reportlab/file/tip/src/reportlab/lib/colors.py#l532.
        """
        # Update the base style, as applicable
        self.base_style = base or self.base_style
        # Update style attributes, as applicable
        self.font = font_name or self.font
        self.font_size = font_size or self.font_size
        self.font_color = font_color or self.font_color
        self.left_indent = left_indent if left_indent is not None else self.left_indent
        self.right_indent = right_indent if right_indent is not None else self.right_indent
        self.alignment = alignment or self.alignment
        self.background_color = background_color or self.background_color
        if self.background_color == "white":
            self.background_color = None
        self.background_padding = background_padding if background_padding is not None else self.background_padding
        self.leading = leading if leading is not None else self.leading
        if space_between_paragraphs is not None:
            self.space_between_paragraphs = space_between_paragraphs
        # Prepare the new style
        self._style = reportlab.lib.styles.getSampleStyleSheet()[self.base_style]
        self._style.fontName = self.font
        self._style.fontSize = self.font_size
        self._style.textColor = self.font_color
        self._style.leftIndent = self.left_indent * reportlab.lib.units.inch
        self._style.rightIndent = self.right_indent * reportlab.lib.units.inch
        self._style.alignment = {"left": 0, "center": 1, "right": 2, "justify": 4}[self.alignment]
        self._style.leading = self.leading
        self._style.spaceBefore = self.space_between_paragraphs
        self._style.spaceAfter = self.space_between_paragraphs
        self._style.backColor = self.background_color
        self._style.borderPadding = self.background_padding if self.background_color else 0

    def write(self, text):
        """Write the given text to the PDF, in the current style.

        Args:
            text:
                The text to write to the PDF.
        """
        for paragraph in text.split('\n'):
            while '  ' in paragraph:
                paragraph = paragraph.replace("  ", "&nbsp;&nbsp;")
            self._contents.append(reportlab.platypus.Paragraph(text=paragraph, style=self._style))

    def insert_title_page(self, title, author=None, alignment='center', image_filename=None, image_width=None):
        """Generate a basic title page.

        Note: You can always create a title page in a custom style by using the PDF.style() and PDF.write()
        commands, as you do for the rest of the book contents.

        Args:
            title:
                The title to display on the title page.
            author:
                The author, if any, to display on the title page.
            alignment:
                The alignment for the title page. Must be one of {"left", "center", "right", "justify"}.
            image_filename:
                The filepath at which the image, if any, is located.
            image_width:
                The width at which to render the image, if any, in the PDF.
            image_height:
                The height at which to render the image, if any, in the PDF.
        """
        current_style = self.base_style
        self.style(base="Title", alignment=alignment)
        self.write(text=title)
        if author:
            self._style.fontSize = self.font_size * 0.5
            self.write(text=f"{author}")
        if image_filename:
            self.insert_image(filename=image_filename, width=image_width)
        self.insert_page_break()
        self.style(base=current_style)

    def insert_space(self, height=None):
        """Insert vertical space.

        Args:
            height:
                The amount of vertical space to insert, if any, in inches. If None, defaults to the current font size.
        """
        height_in_points = (height * reportlab.lib.units.inch) if height else self.font_size
        self._contents.append(reportlab.platypus.Spacer(width=5, height=height_in_points))  # Width doesn't matter

    def insert_page_break(self):
        """Insert a page break."""
        self._contents.append(reportlab.platypus.PageBreak())

    def insert_image(self, filename, width=None):
        """Insert an image into the PDF.

        Args:
            filename:
                The filepath at which the image is located.
            width:
                The width at which to render the image in the PDF. The image's proportions will be maintained.
        """
        width_in_points = width * reportlab.lib.units.inch if width else None  # Convert to points
        image = reportlab.platypus.Image(
            filename=filename,
            width=width_in_points,
            height=width_in_points,
            kind='proportional'
        )
        self._contents.append(image)

    def build(self, page_numbers=True):
        """Generate an actual PDF file at the filename originally passed to self.__init__().

        Args:
            page_numbers:
                Whether page numbers should be added to the rendered PDF. Page numbers will not be included on the first
                page of the PDF.
        """
        if page_numbers:
            self._doc.build(flowables=self._contents, onLaterPages=self._add_page_numbers)
        else:
            self._doc.build(flowables=self._contents)

    def _add_page_numbers(self, canvas, doc):
        """This is a callback function that will be used to add page numbers, if self.page_numbers is True."""
        canvas.saveState()
        canvas.setFont(self.font, self.font_size)
        page_number_text = f"{doc.page}"
        canvas.drawCentredString(
            0.75 * reportlab.lib.units.inch,
            0.75 * reportlab.lib.units.inch,
            page_number_text
        )
        canvas.restoreState()
