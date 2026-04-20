addEventListener("load", (event) => {
    function flatten_table(table) {
        const table_body = table.getElementsByTagName("tbody")[0];
        const rows = table_body.getElementsByTagName("tr");
        for (const row of rows) {
            const cells = row.getElementsByTagName("td");
            if (cells[0].classList.contains("tpad")) {
                cells[1].setAttribute("colspan", "2");
                for (const tspan of [...cells[1].getElementsByClassName("tspan")]) {
                    tspan.remove();
                }
                cells[0].remove();
            }
        }
    }

    function sort_table(table) {
        flatten_table(table);
        const table_body = table.getElementsByTagName("tbody")[0];
        const rows = table_body.getElementsByTagName("tr");
        const dates = [...rows].map(row => [row, row.getElementsByClassName("sv")[0].innerText]);
        dates.sort((a, b) => a[1] > b[1] ? 1 : -1);
        for (const row of dates) {
            table_body.appendChild(row[0]);
        }
    }

    function reverse_table_rows(table) {
        const table_body = table.getElementsByTagName("tbody")[0];
        const reversed_rows = [...table_body.rows].reverse();
        for (const row of reversed_rows) {
            table_body.appendChild(row);
        }
    }

    const sort_icon = document.getElementsByClassName("survey-sort");

    for (const icon of sort_icon) {
        icon.addEventListener("click", (event) => {
            event.preventDefault();
            const table = event.target.closest('table');
            const cl = event.target.closest('a').getElementsByTagName("i")[0].classList;
            // Table not already sorted, perform initial sort
            if (cl.contains("fa-arrow-down-up-across-line")) {
                sort_table(table);
                cl.remove("fa-arrow-down-up-across-line");
                cl.add("fa-arrow-down");
            } else {  // Table already sorted, just reverse the table row list
                reverse_table_rows(table);
                if (cl.contains("fa-arrow-up")) {
                    cl.remove("fa-arrow-up");
                    cl.add("fa-arrow-down");
                } else {
                    cl.remove("fa-arrow-down");
                    cl.add("fa-arrow-up");
                }
            }
        })
    }

});