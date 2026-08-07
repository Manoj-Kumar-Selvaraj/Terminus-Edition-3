package formatx

import "strconv"

// ThousandsGroup renders a value with the thousands group rule.
func ThousandsGroup(value int64) string {
	negative := value < 0
	absolute := value
	if negative {
		absolute = -absolute
	}
	digits := strconv.FormatInt(absolute, 10)
	grouped := make([]byte, 0, len(digits)+len(digits)/3)
	count := 0
	for i := len(digits) - 1; i >= 0; i-- {
		grouped = append(grouped, digits[i])
		count++
		if count%3 == 0 && i > 0 {
			grouped = append(grouped, ',')
		}
	}
	for i, j := 0, len(grouped)-1; i < j; i, j = i+1, j-1 {
		grouped[i], grouped[j] = grouped[j], grouped[i]
	}
	if negative {
		return "-" + string(grouped)
	}
	return string(grouped)
}
