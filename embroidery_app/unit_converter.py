class UnitConverter:
    MM10_PER_CM = 100  # 1 cm = 10 mm = 100 (1/10 mm)

    @staticmethod
    def mm10_to_cm(value_mm10: float) -> float:
        """Converts a value from 1/10 millimeters to centimeters."""
        return value_mm10 / UnitConverter.MM10_PER_CM

    @staticmethod
    def get_pattern_size_cm(pattern_bounds_mm10) -> tuple[float, float] | None:
        """
        Calculates the pattern's width and height in centimeters.
        pattern_bounds_mm10: A QRectF object representing the pattern bounds in 1/10mm units.
        Returns a tuple (width_cm, height_cm) or None if bounds are invalid.
        """
        if not pattern_bounds_mm10 or not pattern_bounds_mm10.isValid():
            return None
        
        width_cm = UnitConverter.mm10_to_cm(pattern_bounds_mm10.width())
        height_cm = UnitConverter.mm10_to_cm(pattern_bounds_mm10.height())
        return width_cm, height_cm