
$(document).ready(function(){
    $.get("status.json", update_state);
})
function start(){
    $.post("start.json",
    {
        title: $("#title").val(),
        content: $("#content").val()
    }, update_state);
    $("#title").val("");
    $("#content").val("");
}

function stop(){
    $.post("stop.json", update_state);
}

function update_state(data){
    console.log(data)
    if(data.recording){
        $("#stopped").hide()
        $("#recording").show()
    } else {
        $("#recording").hide()
        $("#stopped").show()
    }
    $("#filename").text(data.filename);
}

