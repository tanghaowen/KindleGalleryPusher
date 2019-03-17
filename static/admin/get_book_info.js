
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
        csrf = document.querySelector("input[name='csrfmiddlewaretoken']").value
        var data = "site=bangumi&book_id="+bangumi_id+"&csrfmiddlewaretoken="+csrf;
        xmlhttp.send(data);

    };
    document.getElementById("update_book_info_mangazenkan").onclick = function () {
        var mangazenkan_path = document.getElementById("id_mangazenkan_site_path").value;
        if (mangazenkan_path == ''){return}
        onhttpload = function () {
            location.reload();
        };
        book_id = document.getElementById("update_book_info_mangazenkan").getAttribute("book_id");
        var xmlhttp = new XMLHttpRequest();
        xmlhttp.onload = onhttpload;
        xmlhttp.open('post','/book/'+book_id+'/getinfofrom/',true);
        xmlhttp.setRequestHeader("Content-Type","application/x-www-form-urlencoded");
        csrf = document.querySelector("input[name='csrfmiddlewaretoken']").value
        var data = "site=mangazenkan&book_id="+mangazenkan_path+"&csrfmiddlewaretoken="+csrf;
        xmlhttp.send(data);

    }
    document.getElementById("update_book_info_mediaarts").onclick = function () {

    }
}

function setVolumeIndex() {
    inputs = document.querySelectorAll(".inline-related input.vTextField");
    for (let i in inputs) {
        let input = inputs[i];
        let i_int = parseInt(i);
        if (i_int+1 == inputs.length) {
            continue
        }
        if (input.value == "" && !isNaN(i_int)){

            input.value = i_int+1;

        }

    }
    
}
window.addEventListener('load',setButton);
window.addEventListener('load',setVolumeIndex);
window.addEventListener('load',function () {
    document.getElementsByClassName('add-row')[0].children[0].addEventListener('click',setVolumeIndex);
})