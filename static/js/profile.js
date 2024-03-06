document.getElementById('image_upload_btn').addEventListener('click', function() {
    document.getElementById('hidden_file_input').click();
});

document.getElementById('hidden_file_input').addEventListener('change', function() {
    var file = this.files[0];
    if (file) {
        var formData = new FormData();
        formData.append('file', file);

        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload_profile_pic', true);

        xhr.onload = function() {
            if (this.status == 200) {
                alert('Image uploaded successfully!');
            } else {
                alert('Error uploading image.');
            }
        };

        xhr.send(formData);
    }
});
