document.addEventListener('DOMContentLoaded', () => {
    const observer = new MutationObserver(() => {
        const targetRow = document.querySelector('.dt-table-container__row-0');
        console.log(targetRow)
        if (targetRow) {
            const cells = targetRow.getElementsByTagName('td');
            console.log(cells)
            Array.from(cells).forEach(cell => {
                const cellValue = parseFloat(cell.innerText);
                if (!isNaN(cellValue) && cellValue < 7.8) {
                    cell.classList.add("red");
                } else {
                    cell.classList.remove("red");
                }
            });
            
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
});
