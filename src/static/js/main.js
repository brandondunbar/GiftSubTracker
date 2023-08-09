// Handle the Reward button functionality
$(document).ready(function(){
    $(".reward-button").click(function(e){
        e.preventDefault();
        var user_id = $(this).data('userid');
        var row = $(this).closest('tr');
        $.ajax({
            url: '/reward',
            type: 'post',
            data: {'user_id': user_id},
            success: function(response){
                if(response.success){
                    // Update the rewards_given field in the table
                    var rewardsCell = row.find('.rewards-given');
                    var newRewards = response.new_data.rewards_given;
                    rewardsCell.text(newRewards);
                } else {
                    console.log('Failed to increment rewards');
                }
            },
            error: function(response){
                console.log('Error:', response);
            }
        });
    });
});

var socket = io.connect('https://' + location.hostname + ':' + location.port);
socket.on('update_gifters', function(data) {
    // Get the table body
    var tableBody = document.getElementById('gifters-table-body');

    // Check if a row for this user already exists
    var existingRow = document.getElementById(data.user_id);
    if (existingRow) {
        // User row already exists, update the number of gifted subs
        var giftedSubsCell = existingRow.cells[1];
        var existingGiftedSubs = parseInt(giftedSubsCell.innerText);
        giftedSubsCell.innerText = existingGiftedSubs + data.gifted_subs;
    } else {
        // Create a new row
        var row = document.createElement('tr');
        row.id = data.user_id;

        // Create cells for each piece of data
        var userNameCell = document.createElement('td');
        userNameCell.textContent = data.user_name;
        row.appendChild(userNameCell);

        var giftedSubsCell = document.createElement('td');
        giftedSubsCell.textContent = data.gifted_subs;
        row.appendChild(giftedSubsCell);

        var rewardsGivenCell = document.createElement('td');
        rewardsGivenCell.textContent = data.rewards_given;
        row.appendChild(rewardsGivenCell);

        // Add a button to increment the rewards_given
        var buttonCell = document.createElement('td');
        var button = document.createElement('button');
        button.textContent = 'Reward';
        button.onclick = function() {
            incrementRewards(data.user_id);
        };
        buttonCell.appendChild(button);
        row.appendChild(buttonCell);

        // Add the new row to the table
        tableBody.appendChild(row);
    }
});
