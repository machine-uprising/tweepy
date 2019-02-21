# Tweepy Direct Message Utilities
# written by David Standish (https://github.com/machine-uprising)
# February 2019
#
# Tweepy
# Copyright 2010 Joshua Roesslein
# See LICENSE for details.

def dm_quick_reply(quick_reply):
    """ Direct Message Send with Quick Reply Validation
    - Validates the quick reply options being sent with a direct message
    :reference:https://developer.twitter.com/en/docs/direct-messages/quick-replies/overview
    """
    qr_valid_keys = ['type','options']
    qr_option_valid_keys = ['label','description','metadata']

    qr_keys = list(quick_reply.keys())
    for key in qr_keys:
        if key not in qr_valid_keys:
            return 'Quick reply is missing required key - %s'%key

    if not isinstance(quick_reply['options'],list):
        return 'Quick reply error. options value should a list type'

    if len(quick_reply['options']) == 0:
        return 'Quick reply does not have any options'
    elif len(quick_reply['options']) > 20:
        return 'Quick reply can only have max of 20 options'

    for option in quick_reply['options']:
        if not isinstance(option,dict):
            return 'Quick reply option error. Each options must be dict() object'

        option_keys = list(option.keys())
        if len(option_keys) == 0:
            return 'Quick reply object has no content'

        if 'label' not in option_keys:
            return 'Quick reply option must have label specified'
        for key in option_keys:
            if key not in qr_option_valid_keys:
                return 'Quick reply option has invalid key - %s'%key

    return None

def dm_cta_buttons(cta_buttons):
    """ Direct Message Send with Call to Action Buttons Validation
    - Validates the call to action buttons being sent with a direct message
    :reference: https://developer.twitter.com/en/docs/direct-messages/buttons/api-reference/buttons
    """
    ctas_valid_keys = ['type','label','url']

    if len(cta_buttons) > 3:
        return 'CTA Buttons Error. You can only have a max of 3 buttons'

    for button in cta_buttons:
        if not isinstance(button,dict):
            return 'CTA Button Error. Buttons must be dict objects'

        button_keys = list(button.keys())
        for key in button_keys:
            if key not in ctas_valid_keys:
                return 'CTA Button Error. Invalid button key - %s'%key

    return None
