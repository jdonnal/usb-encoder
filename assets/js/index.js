$(function () {
    setInterval(loadData, 2000);
    $("#update-interval").val(loadData);
});

function loadData(){
    $.get("data.json", function (data) {
        $("#data").text(data['random_value']);
    });
}

function change_bkgd(){
    let color = parseInt(Math.random()*0xFFFFFF).toString(16);
    $(".jumbotron").css("background", "#"+color);
}

function stop_recording() {
	$.post("turnoff");
}

function start_recording() { 
	$.post("turnon");
}
