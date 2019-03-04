
function setButton(){
    document.getElementById("update_book_info_banmgumi").onclick = function () {
        var bangumi_id = document.getElementById("id_bangumi_site_path").valueAsNumber;
        if (isNaN(bangumi_id)){
            return;
        }
        onhttpload = function () {
            location.reload();
        }
        book_id = document.getElementById("update_book_info_banmgumi").getAttribute("book_id")
        var xmlhttp = new XMLHttpRequest();
        xmlhttp.onload = onhttpload;
        xmlhttp.open('post','/book/'+book_id+'/getinfofrom/',true);
        xmlhttp.setRequestHeader("Content-Type","application/x-www-form-urlencoded");
        var data = "site=bangumi&book_id="+bangumi_id;
        xmlhttp.send(data);

    }
    document.getElementById("update_book_info_mediaarts").onclick = function () {

    }
}
window.addEventListener('load',setButton);
