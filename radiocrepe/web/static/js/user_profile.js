$(function(){
    $('#user_name').qtip({
        content: $("#userpop"),
        show: {
            event: 'click'
        },
        hide: {
            event: 'unfocus'
        },
        style: {
            classes: 'ui-tooltip-dark ui-tooltip-shadow ui-tooltip-rounded'
        },
        position: {
            my: 'top right',
            at: 'bottom center'
        }
    });

    $('#key_button').qtip({
        content: {
	    text: 'Loading...',
	    title: {
		text: 'Your Service Keys',
		button: true
	    },
            ajax: {
                url: '/user/keys/',
                type: 'GET',
                data: {},
                dataType: 'json',
                success: function(data, status) {
                    var template = Handlebars.compile($("#key_template").html());
                    this.set('content.text', template(data));
                }
            }
	},
        position: {
	    my: 'center',
	    at: 'center',
	    target: $(window)
	},
	show: {
	    event: 'click',
	    solo: true,
	    modal: true
	},
        style: {
            width: '400px',
            classes: 'ui-tooltip-light ui-tooltip-rounded'
        }
    });
});
